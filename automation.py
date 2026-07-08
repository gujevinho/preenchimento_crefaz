"""
Módulo de automação de preenchimento de proposta na Crefazon.

Segurança:
- Login e senha do sistema NUNCA ficam no código. São lidos de variáveis
  de ambiente (CREFAZON_LOGIN / CREFAZON_SENHA), configuradas no painel
  do Render (ou em um .env local, que não deve ser commitado no git).
- Os dados do cliente (CPF, nome, telefone, etc.) chegam via parâmetro
  `dados`, vindos da requisição HTTP — nada fica fixo no código.
"""

import os
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger("automation")

CREFAZON_URL = "https://crefazon.com.br/login"


def _criar_driver() -> webdriver.Chrome:
    """Cria o driver do Chrome configurado para rodar headless em produção."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def _validar_credenciais():
    login = os.getenv("CREFAZON_LOGIN")
    senha = os.getenv("CREFAZON_SENHA")
    if not login or not senha:
        raise RuntimeError(
            "Credenciais CREFAZON_LOGIN / CREFAZON_SENHA não configuradas "
            "nas variáveis de ambiente."
        )
    return login, senha


def _validar_dados_obrigatorios(dados: dict):
    obrigatorios = ["cpf", "nome", "data_nascimento", "telefone", "cep", "cod_instalacao, data_leitura"]
    faltando = [campo for campo in obrigatorios if not dados.get(campo)]
    if faltando:
        raise ValueError(f"Campos obrigatórios ausentes: {', '.join(faltando)}")


def preencher_formulario(dados: dict) -> dict:
    """
    Executa o login na Crefazon e o preenchimento de uma nova proposta.

    Args:
        dados: dicionário com os dados do cliente, ex:
            {
                "cpf": "24748333820",
                "nome": "Leandro Gujev Firmino",
                "data_nascimento": "14/12/1974",
                "telefone": "17996795804",
                "cep": "15501096",
                "ocupacao": "Assalariado",     # opcional, default "Assalariado"
                "possui_veiculo": True,          # opcional, default True
                "cod_instalacao": "24748333820",
                "data_leitura": "14/12/1974"
            }

    Returns:
        dict com o resultado da execução.
    """
    _validar_dados_obrigatorios(dados)
    login, senha = _validar_credenciais()

    ocupacao = dados.get("ocupacao", "Assalariado")
    possui_veiculo = dados.get("possui_veiculo", True)

    logger.info(f"Iniciando automação para CPF {dados['cpf'][:3]}***")

    driver = _criar_driver()
    wait = WebDriverWait(driver, 15)

    try:
        # ---------- LOGIN ----------
        driver.get(CREFAZON_URL)

        campo_login = wait.until(EC.visibility_of_element_located((By.NAME, "login")))
        campo_login.send_keys(login)

        campo_senha = wait.until(EC.visibility_of_element_located((By.NAME, "senha")))
        campo_senha.send_keys(senha)

        botao_enviar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        botao_enviar.click()
        time.sleep(3)

        # Fecha modal pós-login, se aparecer
        try:
            botao_fechar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/div[2]/div/div[2]/button"))
            )
            botao_fechar.click()
        except Exception:
            logger.info("Modal pós-login não apareceu, seguindo em frente")

        # ---------- NAVEGAÇÃO ATÉ NOVA PROPOSTA ----------
        botao_credito = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Crédito']")))
        botao_credito.click()
        time.sleep(3)

        botao_proposta = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Proposta']")))
        botao_proposta.click()

        botao_novaproposta = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-cy='menu-nova-proposta']"))
        )
        botao_novaproposta.click()

        body = driver.find_element(By.TAG_NAME, "body")

        # ---------- DADOS DO CLIENTE ----------
        campo_cpf = wait.until(EC.visibility_of_element_located((By.NAME, "cpf")))
        campo_cpf.send_keys(dados["cpf"])
        ActionChains(driver).move_to_element(body).click().perform()
        time.sleep(2)

        campo_nome = wait.until(EC.visibility_of_element_located((By.NAME, "nome")))
        campo_nome.send_keys(dados["nome"])

        campo_data_nasc = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Selecionar data']"))
        )
        campo_data_nasc.send_keys(dados["data_nascimento"])
        ActionChains(driver).move_to_element(body).click().perform()
        time.sleep(2)

        campo_telefone = wait.until(EC.visibility_of_element_located((By.NAME, "telefone")))
        campo_telefone.send_keys(dados["telefone"])
        time.sleep(2)
        ActionChains(driver).move_to_element(body).click().perform()

        # ---------- OCUPAÇÃO (select com busca) ----------
        select_ocupacao = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-cy='ocupacaoId']"))
        )
        select_ocupacao.click()

        input_busca = select_ocupacao.find_element(
            By.CSS_SELECTOR, "input.ant-select-selection-search-input"
        )
        input_busca.send_keys(ocupacao)
        time.sleep(1)

        opcao_ocupacao = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//div[contains(@class,'ant-select-item-option') and contains(@title,'{ocupacao}')]")
            )
        )
        opcao_ocupacao.click()
        time.sleep(2)

        # ---------- CEP ----------
        campo_cep = wait.until(EC.visibility_of_element_located((By.NAME, "cep")))
        campo_cep.send_keys(dados["cep"])

        # ---------- POSSUI VEÍCULO ----------
        texto_veiculo = "Sim" if possui_veiculo else "Não"
        botao_veiculo = wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//span[normalize-space()='{texto_veiculo}']"))
        )
        botao_veiculo.click()

        # ---------- AVANÇAR ----------
        botao_avancar = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='AVANÇAR']")))
        botao_avancar.click()
        time.sleep(10)

        # ---------- SIMULAR ----------
        botao_simular = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='row main-area']//div[2]//div[1]//div[2]//button[1]")))
        botao_simular.click()
        time.sleep(3)

        # ---------- DADOS INSTALAÇÂO ----------
        campo_instalacao = wait.until(EC.visibility_of_element_located((By.NAME, "adicionais.0.valor")))
        campo_instalacao.click()
        #inserido click para liberar o campo
        campo_instalacao.send_keys(dados["cod_instalacao"])

        campo_data_leitura = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Selecionar data']"))
        )
        campo_data_leitura.send_keys(dados["data_leitura"])
        ActionChains(driver).move_to_element(body).click().perform()
        time.sleep(2)

        botao_consultar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Consultar valores']")))
        botao_consultar.click()
        time.sleep(10)

        ActionChains(driver).move_to_element(body).click().perform()
        time.sleep(2)
        ActionChains(driver).send_keys(Keys.TAB).perform()
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        select_input = driver.find_element(By.ID, "rc_select_5")
        select_input.click()
        select_input.send_keys(Keys.ENTER)

        time.sleep(3)

        botao_calcular = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='CALCULAR']")))
        botao_calcular.click()
        time.sleep(3)

        botao_prazo = wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[normalize-space()='{texto_veiculo}']")))
        botao_prazo.click()

        radio_input = driver.find_element(By.XPATH, "//input[@type='radio' and @class='ant-radio-input']")
        driver.execute_script("arguments[0].click();", radio_input)

        botao_cadastrar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='CADASTRAR']")))
        botao_cadastrar.click()
        time.sleep(3)


        logger.info("Automação concluída com sucesso")
        return {"sucesso": True, "mensagem": "Proposta preenchida com sucesso"}

    except Exception as e:
        logger.exception("Erro ao executar automação")
        return {"sucesso": False, "mensagem": str(e)}

    finally:
        driver.quit()
