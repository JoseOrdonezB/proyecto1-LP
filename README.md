# Proyecto 1 - Generador de analizadores léxicos y sintácticos

Aplicación en Streamlit para generar y probar analizadores léxicos a partir de
archivos YALex (`.yal`) y analizadores sintácticos a partir de archivos YAPar
(`.yalp`).

El proyecto permite cargar especificaciones, construir autómatas, generar tablas,
visualizar resultados y ejecutar análisis sobre texto de entrada.

## Funcionalidades principales

- Parser de archivos YALex.
- Construcción de AFN con Thompson.
- Conversión de AFN a AFD.
- Minimización de AFD.
- Generación de código Python para el lexer.
- Parser de archivos YAPar.
- Construcción del autómata LR(0).
- Construcción de tabla sintáctica con reducciones por `FOLLOW` estilo SLR.
- Validación de tokens declarados en YAPar contra tokens retornados por YALex.
- Generación de código Python independiente para el parser.
- Ejecución integrada lexer + parser desde la interfaz.
- Pruebas incluidas para complejidad baja, media y alta.

## Requisitos

- Python 3.10 o superior.
- `pip`.
- Navegador web.

Dependencias principales:

- `streamlit`
- `numpy`

## Instalación

Desde la raíz del proyecto:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install streamlit numpy
```

En Windows:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install streamlit numpy
```

## Ejecución

```bash
source venv/bin/activate
streamlit run app.py
```

En Windows:

```bat
venv\Scripts\activate
streamlit run app.py
```

La aplicación normalmente queda disponible en:

```text
http://localhost:8501
```

## Uso de la aplicación

1. En la barra lateral, subir un archivo `.yal`.
2. Subir el archivo `.yalp` correspondiente.
3. Activar o desactivar la opción de minimizar AFD.
4. Presionar `Generar analizadores`.
5. En la pestaña `Ejecutar`, escribir o pegar texto de entrada.
6. Presionar `Analizar`.

La interfaz muestra:

- Tokens generados por el lexer.
- Pasos del parser shift/reduce.
- Errores sintácticos cuando la entrada no pertenece a la gramática.
- AFD léxico.
- Autómata LR(0).
- Tabla de transición del AFD.
- Código generado para `lexer.py`.
- Código generado para `parser.py`.

## Archivos de prueba

Los archivos de prueba están en:

```text
src/data/
```

Cada nivel tiene tres archivos:

```text
bajo.yal    bajo.yalp    bajo.txt
medio.yal   medio.yalp   medio.txt
alto.yal    alto.yalp    alto.txt
```

### Complejidad baja

Archivos:

```text
src/data/bajo.yal
src/data/bajo.yalp
src/data/bajo.txt
```

Entrada válida:

```text
total = x + 5
```

Entrada inválida:

```text
total = + 5
```

### Complejidad media

Archivos:

```text
src/data/medio.yal
src/data/medio.yalp
src/data/medio.txt
```

Entrada válida:

```text
if (x == y) print(x + 1)
```

Entrada inválida:

```text
if (x ==) print(x)
```

### Complejidad alta

Archivos:

```text
src/data/alto.yal
src/data/alto.yalp
src/data/alto.txt
```

Entrada válida:

```text
def factorial(n): if n <= 1: return 1 else: return n * factorial(n - 1)
```

Entrada inválida:

```text
def factorial(n): if n <= : return 1
```

## Validación YAPar contra YALex

Antes de generar el parser, la aplicación valida que todos los tokens declarados
en el archivo `.yalp` también existan como acciones `return TOKEN` en el archivo
`.yal`.

Por ejemplo, si el `.yalp` declara:

```yapar
%token ID NUMBER TOKEN_FALTANTE
```

pero el `.yal` no contiene:

```yal
{ return TOKEN_FALTANTE }
```

la aplicación muestra un error indicando cuáles tokens faltan.

## Estructura del proyecto

```text
app.py                         Interfaz Streamlit
src/parser_yalex.py            Parser de especificaciones YALex
src/automata.py                Thompson, AFN, AFD y minimización
src/codegen.py                 Generador de código del lexer
src/codegen_parser.py          Generador de código del parser
src/syntax/parser_yapar.py     Parser de especificaciones YAPar
src/syntax/lr0.py              Autómata LR(0), FIRST, FOLLOW y tabla SLR
src/syntax/parser_engine.py    Motor shift/reduce
src/syntax/lexer_parser_bridge.py Integración lexer + parser
src/syntax/visualizer.py       Exportación de autómatas a DOT
src/data/                      Archivos de prueba
```

## Notas importantes

- El analizador léxico se construye usando autómatas, no librerías de expresiones regulares.
- El parser generado es independiente del generador: contiene sus tablas `ACTION` y `GOTO`.
- La tabla sintáctica se basa en el autómata LR(0), usando conjuntos `FOLLOW` para reducciones SLR.
- Los comentarios en los archivos de prueba usan `#` y son ignorados por los lexers incluidos.

## Solución de problemas

Si Streamlit no inicia porque el puerto está ocupado:

```bash
streamlit run app.py --server.port 8502
```

Si la app indica tokens faltantes, revisa que los `%token` del `.yalp` tengan
su respectivo `return TOKEN` dentro del `.yal`.

Si una entrada válida falla, verifica que estés usando el `.yal` y `.yalp` del
mismo nivel de complejidad.
