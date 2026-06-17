
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import pandas as pd
from io import BytesIO

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "todo_db"
}

pool = pooling.MySQLConnectionPool(
    pool_name="todo_pool",
    pool_size=5,
    **DB_CONFIG
)

HTML = """
<!DOCTYPE html>
<html>
<head><title>Todo App</title></head>
<body>
<h2>Todo Application</h2>
<input id="title" placeholder="Task title">
<button onclick="addTask()">Add</button>
<ul id="tasks"></ul>
<script>
async function load(){
 let r=await fetch('/tasks');
 let d=await r.json();
 let ul=document.getElementById('tasks');
 ul.innerHTML='';
 d.forEach(t=>{
   ul.innerHTML+=`<li>${t.title} (${t.status})
   <button onclick="del(${t.id})">Delete</button></li>`;
 });
}
async function addTask(){
 await fetch('/tasks',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({title:document.getElementById('title').value})});
 load();
}
async function del(id){
 await fetch('/tasks/'+id,{method:'DELETE'});
 load();
}
load();
</script>
</body>
</html>
"""

def conn():
    return pool.get_connection()

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/tasks", methods=["GET"])
def get_tasks():
    c = conn()
    cur = c.cursor(dictionary=True)
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close(); c.close()
    return jsonify(rows)

@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    c = conn()
    cur = c.cursor(dictionary=True)
    cur.execute("SELECT * FROM tasks WHERE id=%s",(task_id,))
    row = cur.fetchone()
    cur.close(); c.close()
    return jsonify(row or {})

@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.json
    title = data.get("title","").strip()
    if not title:
        return jsonify({"error":"Title required"}),400
    c=conn(); cur=c.cursor()
    cur.execute("""INSERT INTO tasks
    (title,description,priority,status,due_date)
    VALUES(%s,%s,%s,%s,%s)""",
    (title,data.get("description"),data.get("priority","Medium"),
     data.get("status","Pending"),data.get("due_date")))
    c.commit()
    cur.close(); c.close()
    return jsonify({"message":"Task added"})

@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data=request.json
    c=conn(); cur=c.cursor()
    cur.execute("""UPDATE tasks SET
    title=%s, description=%s, priority=%s,
    status=%s, due_date=%s
    WHERE id=%s""",
    (data.get("title"),data.get("description"),
     data.get("priority"),data.get("status"),
     data.get("due_date"),task_id))
    c.commit()
    cur.close(); c.close()
    return jsonify({"message":"Updated"})

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    c=conn(); cur=c.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s",(task_id,))
    c.commit()
    cur.close(); c.close()
    return jsonify({"message":"Deleted"})

@app.route("/tasks/<int:task_id>/complete", methods=["PUT"])
def complete_task(task_id):
    c=conn(); cur=c.cursor()
    cur.execute("UPDATE tasks SET status='Completed' WHERE id=%s",(task_id,))
    c.commit()
    cur.close(); c.close()
    return jsonify({"message":"Completed"})

@app.route("/tasks/export-excel")
def export_excel():
    c=conn()
    df=pd.read_sql("SELECT * FROM tasks", c)
    c.close()
    output=BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer,index=False)
    output.seek(0)
    return send_file(output, download_name="tasks.xlsx", as_attachment=True)

@app.route("/tasks/import-excel", methods=["POST"])
def import_excel():
    file=request.files["file"]
    df=pd.read_excel(file)
    c=conn(); cur=c.cursor()
    for _,row in df.iterrows():
        if "action" in df.columns and str(row.get("action","")).upper()=="DELETE":
            cur.execute("DELETE FROM tasks WHERE id=%s",(int(row["id"]),))
        elif pd.notna(row.get("id")):
            cur.execute("""UPDATE tasks SET title=%s,description=%s,
            priority=%s,status=%s,due_date=%s WHERE id=%s""",
            (row.get("title"),row.get("description"),row.get("priority"),
             row.get("status"),row.get("due_date"),int(row.get("id"))))
        else:
            cur.execute("""INSERT INTO tasks(title,description,priority,status,due_date)
            VALUES(%s,%s,%s,%s,%s)""",
            (row.get("title"),row.get("description"),row.get("priority"),
             row.get("status"),row.get("due_date")))
    c.commit()
    cur.close(); c.close()
    return jsonify({"message":"Import completed"})

if __name__ == "__main__":
    app.run(debug=True)
