import sys
import sqlite3
from cryptography.fernet import Fernet
from pathlib import Path

DB_PATH = Path("passwords.db")
KEY_PATH = Path("key.key")


def get_or_create_key():

    if KEY_PATH.exists():
        key = KEY_PATH.read_bytes()

    else:
        key = Fernet.generate_key()
        KEY_PATH.write_bytes(key)
        print(f"Info? Ключ шифрования создан и сохранён в {KEY_PATH}. Храните его в безопасности!")

    return key


def init_db(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def add_password(conn, fernet, raw_input):

    if ":" not in raw_input:
        print("Ошибка: строка должна быть в формате 'Label:Password'")
        return

    token = fernet.encrypt(raw_input.encode("utf-8"))
    cur = conn.cursor()
    cur.execute("INSERT INTO passwords (data) VALUES (?);", (token,))
    conn.commit()

    print(f"Ok Добавлено (ID: {cur.lastrowid}).")


def view_all(conn, fernet):

    cur = conn.cursor()
    cur.execute("SELECT id, data, created_at FROM passwords ORDER BY id;")
    rows = cur.fetchall()

    if not rows:
        print("Info? База пуста.")
        return

    print("ID | Date                 | Label : Password")
    print("---+----------------------+---------------------------")

    for r in rows:
        _id, blob, created_at = r
        try:
            plain = fernet.decrypt(blob).decode("utf-8")
        except Exception as e:
            plain = f"[ERROR: не удалось расшифровать — {e}]"
        print(f"{_id:>2} | {created_at:<20} | {plain}")


def delete_by_id(conn, id_to_delete):

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM passwords WHERE id = ?;", (id_to_delete,))
    cnt = cur.fetchone()[0]

    if cnt == 0:
        print(f"Warn! Запись с ID: {id_to_delete} не найдена.")
        return

    cur.execute("DELETE FROM passwords WHERE id = ?;", (id_to_delete,))
    conn.commit()

    print(f"Ok Удалено ID: {id_to_delete}.")


def main():

    key = get_or_create_key()
    f = Fernet(key)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    print("=== Менеджер паролей ===")
    print()
    print("Меню:")
    print("1 — Просмотреть все пароли.")
    print("2 — Добавить пароль.")
    print("3 — Удалить по ID.")
    print("4 — Выход.")

    while True:
        print()

        try:
            choice = input("Ввод: ").strip()

            if choice == "1":
                view_all(conn, f)

            elif choice == "2":
                s = input("Введи запись 'Label:Password': ").strip()

                if s == "":
                    print("Warn! Пустая строка — отмена.")
                    continue

                add_password(conn, f, s)

            elif choice == "3":
                id_str = input("Введи ID для удаления: ").strip()

                if not id_str.isdigit():
                    print("Warn! ID должен быть целым числом.")
                    continue

                confirm = input(f"Подтвердить удаление ID: {id_str} ??? (Y/N): ").strip().lower()

                if confirm == "y" or confirm == "Y" or confirm == "yes" or confirm == "Yes":
                    delete_by_id(conn, int(id_str))

                else:
                    print("Отмена удаления.")

            elif choice == "4":
                print("Выход из програми.")
                break

            else:
                print("Неизвестный выбор. Попробуй ещё.")

        except KeyboardInterrupt:
            print("\nПрерывание — выхожу.")
            break

        except Exception as e:
            print(f"Error Что-то пошло не так: {e}")

    conn.close()


if __name__ == "__main__":
    main()
