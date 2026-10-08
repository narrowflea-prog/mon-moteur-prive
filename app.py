import streamlit as st
import sqlite3
from datetime import datetime
import json
import os

# Configuration de la page
st.set_page_config(page_title="Mon Moteur Privé", page_icon="🔒", layout="centered")

DB_FILE = "database.db"

# --- INITIALISATION ET GESTION DE LA BASE SQLITE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Table des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    name TEXT,
                    role TEXT,
                    tokens INTEGER
                )''')
    
    # Table des cibles (Base de données OSINT/Fuites)
    c.execute('''CREATE TABLE IF NOT EXISTS targets (
                    query_key TEXT PRIMARY KEY,
                    data_json TEXT
                )''')
    
    # Table de l'historique
    c.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    user TEXT,
                    type TEXT,
                    target TEXT
                )''')
    
    # Comptes par défaut si la table est vide
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES ('admin', 'MonMotDePasseAdmin123!', 'Administrateur (Toi)', 'admin', 999999)")
        c.execute("INSERT INTO users VALUES ('client1', 'PasswordClient123!', 'Jean Dupont', 'client', 5)")
        
        # Données de démo
        demo_1 = {"Nom": "John Doe", "Téléphone": "+33 6 12 34 56 78", "Adresse IP": "192.168.1.45", "Fuites d'origines": ["Breach2023"], "Statut": "Trouvé"}
        demo_2 = {"Nom": "Alice Martin", "Email": "alice.m@live.fr", "Discord": "AliceM#1234", "Fuites d'origines": ["Forum Leak 2024"], "Statut": "Trouvé"}
        c.execute("INSERT INTO targets VALUES ('john.doe@gmail.com', ?)", (json.dumps(demo_1, ensure_ascii=False),))
        c.execute("INSERT INTO targets VALUES ('0601020304', ?)", (json.dumps(demo_2, ensure_ascii=False),))

    conn.commit()
    conn.close()

# Création/Vérification de la base SQLite
init_db()

# --- FONCTIONS UTILITAIRES SQLITE ---
def get_db_connection():
    return sqlite3.connect(DB_FILE)

def get_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username, password, name, role, tokens FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "password": row[1], "name": row[2], "role": row[3], "tokens": row[4]}
    return None

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username, name, role, tokens FROM users")
    rows = c.fetchall()
    conn.close()
    return [{"username": r[0], "name": r[1], "role": r[2], "tokens": r[3]} for r in rows]

def update_user_tokens(username, tokens):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET tokens = ? WHERE username = ?", (tokens, username))
    conn.commit()
    conn.close()

def create_user(username, password, name, role, tokens):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (username, password, name, role, tokens))
    conn.commit()
    conn.close()

def delete_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def search_target(query):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT data_json FROM targets WHERE query_key = ?", (query.lower(),))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def add_history_entry(user, search_type, target):
    conn = get_db_connection()
    c = conn.cursor()
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute("INSERT INTO history (date, user, type, target) VALUES (?, ?, ?, ?)", (date_str, user, search_type, target))
    conn.commit()
    conn.close()

def get_history(user=None, is_admin=False):
    conn = get_db_connection()
    c = conn.cursor()
    if is_admin:
        c.execute("SELECT date, user, type, target FROM history ORDER BY id DESC")
    else:
        c.execute("SELECT date, user, type, target FROM history WHERE user = ? ORDER BY id DESC", (user,))
    rows = c.fetchall()
    conn.close()
    return [{"date": r[0], "user": r[1], "type": r[2], "target": r[3]} for r in rows]

def get_db_metrics():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    nb_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM targets")
    nb_targets = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM history")
    nb_history = c.fetchone()[0]
    conn.close()
    return nb_users, nb_targets, nb_history

# --- INITIALISATION DE LA SESSION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

# --- PAGE DE CONNEXION ---
def show_login():
    st.title("🔒 Connexion à votre compte")
    
    username_input = st.text_input("Identifiant / Nom d'utilisateur").strip().lower()
    password_input = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter", type="primary"):
        user = get_user(username_input)
        if user and user["password"] == password_input:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username_input
            st.success("Connexion réussie !")
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")

# --- PAGE PRINCIPALE ---
def show_dashboard():
    username = st.session_state["username"]
    user_data = get_user(username)
    
    # BARRE LATÉRALE
    st.sidebar.title(f"Bienvenue, {user_data['name']}")
    st.sidebar.write(f"**Rôle :** {user_data['role'].upper()}")
    
    if user_data['role'] == "admin":
        st.sidebar.success("👑 Accès Administrateur : Jetons illimités")
    else:
        st.sidebar.info(f"🪙 Solde de jetons : **{user_data['tokens']} jetons**")
        
    st.sidebar.divider()
    st.sidebar.subheader("📌 Navigation")
    
    menu_options = ["🔍 Moteur de Recherche", "🌳 Arbre & Proches", "📜 Historique"]
    if user_data['role'] == "admin":
        menu_options.append("⚙️ Panneau Admin")
        
    page = st.sidebar.radio("Choisissez un module :", menu_options)
    
    st.sidebar.divider()
    if st.sidebar.button("Déconnexion", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.rerun()

    # MODULE 1 : RECHERCHE
    if page == "🔍 Moteur de Recherche":
        st.title("🔍 Moteur de Recherche Privé (SQLite)")
        st.write("Saisissez une valeur pour démarrer la recherche.")

        type_recherche = st.selectbox(
            "Type de recherche",
            ["📧 Adresse Email", "📞 Numéro de Téléphone", "👤 Nom / Prénom", "🎮 Pseudo / Discord ID", "🌐 Adresse IP / Domaine"]
        )

        query = st.text_input("Entrez la cible", placeholder="Saisissez votre recherche...").strip().lower()

        if st.button("🚀 Lancer la recherche", type="primary", use_container_width=True):
            if not query:
                st.warning("⚠️ Veuillez entrer un terme à rechercher !")
            elif user_data["role"] != "admin" and user_data["tokens"] <= 0:
                st.error("❌ Solde insuffisant ! Vous n'avez plus de jetons disponibles.")
            else:
                if user_data["role"] != "admin":
                    update_user_tokens(username, user_data["tokens"] - 1)
                
                add_history_entry(username, type_recherche, query)

                st.divider()
                st.subheader("📋 Résultats de la recherche")
                
                res_data = search_target(query)
                if res_data:
                    st.success(f"✅ Correspondance trouvée pour `{query}` !")
                    st.json(res_data)
                    
                    json_string = json.dumps(res_data, indent=4, ensure_ascii=False)
                    st.download_button(
                        label="📥 Télécharger le rapport (JSON)",
                        data=json_string,
                        file_name=f"rapport_{query}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ Aucun résultat trouvé pour la cible : `{query}`")

    # MODULE 2 : ARBRE & PROCHES
    elif page == "🌳 Arbre & Proches":
        st.title("🌳 Arbre Généalogique & Proches")
        st.write("Module de recherche avancée des liens de parenté et contacts proches.")
        
        cible_arbre = st.text_input("Entrez le Nom et Prénom de la cible", placeholder="Ex: Jean Dupont")
        
        if st.button("🔎 Générer l'arbre des proches", type="primary", use_container_width=True):
            if not cible_arbre:
                st.warning("⚠️ Veuillez préciser un nom complet.")
            elif user_data["role"] != "admin" and user_data["tokens"] <= 0:
                st.error("❌ Solde insuffisant pour générer un arbre.")
            else:
                if user_data["role"] != "admin":
                    update_user_tokens(username, user_data["tokens"] - 1)
                
                add_history_entry(username, "🌳 Arbre Généalogique", cible_arbre)

                st.divider()
                st.success(f"Arbre généré avec succès pour : **{cible_arbre}**")
                
                arbre_data = {
                    "Cible principale": cible_arbre,
                    "Famille directe": [
                        {"Relation": "Père", "Nom": "Pierre Dupont", "Âge": 62},
                        {"Relation": "Mère", "Nom": "Marie Curie", "Âge": 59}
                    ]
                }
                st.json(arbre_data)

    # MODULE 3 : HISTORIQUE
    elif page == "📜 Historique":
        st.title("📜 Historique des Recherches")
        user_history = get_history(username, is_admin=(user_data["role"] == "admin"))

        if not user_history:
            st.info("Aucune recherche enregistrée pour le moment.")
        else:
            for item in user_history:
                with st.container(border=True):
                    st.write(f"📅 **Date :** {item['date']} | 👤 **Utilisateur :** {item['user']}")
                    st.write(f"📌 **Type :** {item['type']}")
                    st.write(f"🎯 **Cible :** `{item['target']}`")

    # MODULE 4 : PANNEAU ADMIN
    elif page == "⚙️ Panneau Admin":
        st.title("⚙️ Panneau de Gestion Administrateur")
        
        tab1, tab2, tab3 = st.tabs(["👥 Gestion Utilisateurs", "📂 Base de Données", "📊 Statistiques"])
        
        # TAB 1 : UTILISATEURS
        with tab1:
            st.subheader("➕ Créer un nouveau compte utilisateur")
            with st.form("create_user_form", clear_on_submit=True):
                new_username = st.text_input("Identifiant (Username)").strip().lower()
                new_name = st.text_input("Nom complet du client")
                new_password = st.text_input("Mot de passe", type="password")
                new_role = st.selectbox("Rôle", ["client", "admin"])
                init_tokens = st.number_input("Nombre de jetons initiaux", min_value=1, max_value=1000, value=10)
                
                submit_create = st.form_submit_button("➕ Créer le compte", type="primary")
                
                if submit_create:
                    if not new_username or not new_password or not new_name:
                        st.warning("⚠️ Tous les champs sont obligatoires.")
                    elif get_user(new_username) is not None:
                        st.error("❌ Cet identifiant existe déjà !")
                    else:
                        create_user(new_username, new_password, new_name, new_role, 999999 if new_role == "admin" else init_tokens)
                        st.success(f"Compte `{new_username}` créé avec succès !")
                        st.rerun()

            st.divider()
            st.subheader("🪙 Créditer des jetons")
            all_u = get_all_users()
            client_list = [u for u in all_u if u["role"] == "client"]
            if client_list:
                selected_client_uname = st.selectbox("Sélectionner un client", [c["username"] for c in client_list])
                nb_tokens = st.number_input("Nombre de jetons à ajouter", min_value=1, max_value=100, value=5)
                if st.button("➕ Créditer les jetons"):
                    client_obj = next(c for c in client_list if c["username"] == selected_client_uname)
                    update_user_tokens(selected_client_uname, client_obj["tokens"] + nb_tokens)
                    st.success(f"{nb_tokens} jetons ajoutés au compte `{selected_client_uname}` !")
                    st.rerun()

            st.divider()
            st.subheader("📋 Comptes enregistrés")
            for u in all_u:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• **{u['username']}** ({u['name']}) - Rôle: `{u['role']}` - Jetons: `{u['tokens']}`")
                with col2:
                    if u['username'] != "admin" and u['username'] != username:
                        if st.button("🗑️ Supprimer", key=f"del_{u['username']}"):
                            delete_user(u['username'])
                            st.success(f"Compte `{u['username']}` supprimé.")
                            st.rerun()

        # TAB 2 : GESTION DE LA BASE DE DONNÉES (JSON IMPORT DANS SQLITE)
        with tab2:
            st.subheader("📥 Importer un fichier JSON dans SQLite")
            uploaded_file = st.file_uploader("Choisissez un fichier JSON", type=["json"])
            if uploaded_file is not None:
                try:
                    new_data = json.load(uploaded_file)
                    if isinstance(new_data, dict):
                        conn = get_db_connection()
                        c = conn.cursor()
                        count = 0
                        for k, v in new_data.items():
                            c.execute("INSERT OR REPLACE INTO targets VALUES (?, ?)", (k.lower(), json.dumps(v, ensure_ascii=False)))
                            count += 1
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {count} enregistrement(s) inséré(s) dans SQLite !")
                    else:
                        st.error("❌ Le fichier doit contenir un objet JSON.")
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'import : {e}")

        # TAB 3 : STATISTIQUES
        with tab3:
            st.subheader("📊 Métriques de la plateforme")
            nb_u, nb_t, nb_h = get_db_metrics()
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Utilisateurs", nb_u)
            with col_b:
                st.metric("Cibles en base", nb_t)
            with col_c:
                st.metric("Recherches effectuées", nb_h)

# ROUTAGE
if not st.session_state["logged_in"]:
    show_login()
else:
    show_dashboard()