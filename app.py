import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="kar@2004",
    database="todo_db"
)

cursor = conn.cursor()

while True:
    print("\n1. Add Task")
    print("2. View Tasks")
    print("3. Exit")

    choice = input("Enter choice: ")

    if choice == "1":
        task = input("Enter task: ")

        sql = "INSERT INTO tasks(task_name) VALUES(%s)"
        cursor.execute(sql, (task,))
        conn.commit()

        print("Task Added!")

    elif choice == "2":
        cursor.execute("SELECT * FROM tasks")

        rows = cursor.fetchall()

        print("\nTasks:")
        for row in rows:
            print(row)

    elif choice == "3":
        break

cursor.close()
conn.close()