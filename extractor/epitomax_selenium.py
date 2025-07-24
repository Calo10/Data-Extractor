from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import requests
from ftplib import FTP, FTP_TLS
import os
import tempfile
from pydantic import BaseModel

class FTPConfig(BaseModel):
    host: str
    port: int = 21
    user: str
    password: str
    directory: str = "/"
    use_tls: bool = False
    passive_mode: bool = True

def wait_for_page_load(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def upload_to_ftp(local_file_path, ftp_config: FTPConfig, remote_filename=None):
    if not remote_filename:
        remote_filename = os.path.basename(local_file_path)
    if ftp_config.use_tls:
        ftp = FTP_TLS()
    else:
        ftp = FTP()
    ftp.connect(ftp_config.host, ftp_config.port, timeout=30)
    ftp.login(ftp_config.user, ftp_config.password)
    if ftp_config.use_tls:
        ftp.prot_p()
    if ftp_config.passive_mode:
        ftp.set_pasv(True)
    if ftp_config.directory != "/":
        ftp.cwd(ftp_config.directory)
    with open(local_file_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_filename}", f)
    ftp.quit()

def download_epitomax_pdf_base64(username, password, pdf_url, output_destination="local", ftp_config=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Step 1: Authenticate
        login_url = f"https://my.epitomax.net/epitomax/logout.jsp?j_username={username}&j_password={password}"
        driver.get(login_url)
        wait_for_page_load(driver)
        driver.save_screenshot("after_login.png")

        # Step 2: Extract cookies from Selenium
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # Step 3: Download the PDF using requests with cookies
        resp = session.get(pdf_url)
        if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("application/pdf"):
            pdf_bytes = resp.content
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            filename = "epitomax_form.pdf"
            if output_destination == "local":
                os.makedirs("EpitomaPDF", exist_ok=True)
                local_path = os.path.join("EpitomaPDF", filename)
                with open(local_path, "wb") as f:
                    f.write(pdf_bytes)
                return {"message": "PDF saved locally", "local_path": local_path}
            elif output_destination == "ftp" and ftp_config:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpf:
                    tmpf.write(pdf_bytes)
                    tmpf.flush()
                    upload_to_ftp(tmpf.name, ftp_config, filename)
                return {"message": "PDF uploaded to FTP", "ftp_host": ftp_config.host, "ftp_directory": ftp_config.directory}
            else:
                return {"pdf_base64": pdf_base64}
        else:
            print("Failed to download PDF. Status:", resp.status_code)
            print("Headers:", resp.headers)
            print("Content (first 500 chars):", resp.text[:500])
            raise Exception("Failed to download PDF. Check authentication or URL.")
    finally:
        driver.quit()

# Example usage:
if __name__ == "__main__":
    username = "sysadmin75"
    password = "bm2!pM27TV*XJ6.H"
    pdf_url = "https://my.epitomax.net/epitomax/clinical/Clinical_Print.jsp?display_jsp=Clinical_Print.jsp&file_type=PDFMULTI&episode_id=48&user_action=PRINT_NARRATIVE&case_no=1012&form_id=2241622&formpage_id=2240842&formpage_name=Med%20Review%20Guy%20Page%201&narr_form_id=2241622&menu_item_name=Progress%20Note&problem_group_id=1&company_id=95&dataset=Progress%20Note"
    result = download_epitomax_pdf_base64(username, password, pdf_url, output_destination="local")
    print(result) 