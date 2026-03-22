import streamlit as st

st.set_page_config(page_title="YALex Analyzer", layout="wide")

st.title("🔍 Generador de Analizador Léxico (YALex)")

# =========================
# 📂 Carga de archivo
# =========================

archivo = st.file_uploader("Sube un archivo .yal", type=["yal"])

contenido = None

if archivo is not None:
    contenido = archivo.read().decode("utf-8")

    st.subheader("📄 Contenido del archivo")
    st.code(contenido, language="ocaml")  # estilo yal

# =========================
# ⚙️ Botón de generación
# =========================

if st.button("⚙️ Generar analizador"):

    if contenido is None:
        st.warning("Primero sube un archivo .yal")
    else:
        st.success("Procesando archivo...")


        st.info("🚧 Aquí se integrará el parser de YALex y construcción del AFD")

# =========================
# 📊 Resultados
# =========================

col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 Autómata (AFD)")
    st.write("Aquí se mostrará el autómata generado")

with col2:
    st.subheader("🏷️ Tokens reconocidos")
    st.write("Aquí aparecerán los tokens")

st.subheader("⚠️ Errores léxicos")
st.write("Aquí se mostrarán errores si existen")