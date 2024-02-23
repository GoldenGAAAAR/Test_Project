import logging
import subprocess
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pyats import aetest
from logging import FileHandler
import yaml

#Функция открытия Yaml файла
def open_yaml(yaml_file_path):
    with open(yaml_file_path, 'r') as file:
        config = yaml.safe_load(file)
        return config

#Функция отправки письма на Email
def send_email_notification(device, config):
    # Создаем соединение с SMTP-сервером
    server = smtplib.SMTP(config['smtp_server'])
    server.starttls()
    server.login(config['smtp_username'], config['smtp_password'])
    # Формируем сообщение
    msg = MIMEMultipart()
    msg['From'] = config['email_form']
    msg['To'] = config['email_to']
    msg['Subject'] = f"Failed to ping device {device}"
    body = f"failure to ping device {device} after {config['max_failures']} attempts."
    msg.attach(MIMEText(body, 'plain'))
    # Отправляем сообщение
    server.send_message(msg)
    # Закрываем соединение
    server.quit()

#Функция создания файла с логами
def create_log(config):
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    if os.path.exists(config['log_path']):
        os.remove(config['log_path'])
    file_handler = FileHandler(config['log_path'])
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    return log

###################################################################
###                  COMMON SETUP SECTION                       ###
###################################################################
class common_setup(aetest.CommonSetup):
    @aetest.subsection
    def connect(self, testscript, testbed):
        devices = []
        for device in testbed:
            #Подключение к устройствам
            device.connect()
            devices.append(device)

        #Сохраняем, чтобы можно было использовать в других частях кода
        testscript.parameters['devices'] = devices

###################################################################
###                     TESTCASES SECTION                       ###
###################################################################

class test_up(aetest.Testcase):
    #Настройка устройств
    @aetest.setup
    def send_command(self, devices):
        for device in devices:
            #Отключение ограничения скорости на отправку пакетов
            self.output = device.configure('no ip icmp rate-limit unreachable\nend')

    @aetest.test
    def send_ping(self, devices):
        config = open_yaml('config.yaml')
        log = create_log(config)
        for device in devices:
            attempts = 1
            while attempts <= config['max_failures']:
                #Отправка пинга на устройство
                ping_result = subprocess.run(['ping', '-c', '4', str(device.connections.cli.ip)], stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE, text=True)
                if ping_result.returncode == 0:
                    log.info(f"Ping to {device} ({device.connections.cli.ip}) successful")
                    log.info(ping_result.stdout)
                    break
                else:
                    log.error(f"Failed to ping {device} ({device.connections.cli.ip})g")
                    log.error(ping_result.stderr)
                    attempts += 1
                    #Если попытки исчерпаны, то вызываем функцию отправки письма на Email
                    if attempts == config['max_failures']:
                        send_email_notification(device, config)

#####################################################################
####                       COMMON CLEANUP SECTION                 ###
#####################################################################
class common_cleanup(aetest.CommonCleanup):
    #Отключение устройств
    @aetest.subsection
    def disconnect(self, devices):
        for device in devices:
            device.disconnect()

if __name__ == "__main__":
    main()