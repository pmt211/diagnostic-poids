import pandas as pd
import streamlit as st

st.set_page_config(page_title="Diagnostic du poids")

# Paramètres 
COULEURS = {"Maigreur": "#8B5A2B", "Normal": "#2E8B57", "Surpoids": "#D62728"}  # marron / vert / rouge
MARGE_NOTRE = 0.15  # marge utilisée pour notre formule (modifiable)


# Fonctions 
def diagnostic(poids, poids_normal, marge):
    """Maigreur / Surpoids si le poids s'écarte de plus de 'marge' (ex. 0.15 = 15 %)."""
    if poids < poids_normal * (1 - marge):
        return "Maigreur"
    elif poids > poids_normal * (1 + marge):
        return "Surpoids"
    else:
        return "Normal"


def diagnostic_imc(imc):
    if imc < 18.5:
        return "Maigreur"
    elif imc > 25:
        return "Surpoids"
    else:
        return "Normal"


def calculer(sexe, age, taille, poids):
    """Calcule le poids normal et le diagnostic pour chaque formule.
    Retourne une liste de lignes (une par formule)."""
    broca = taille - 100
    creff = (taille - 100) + 0.09 * age

    if sexe == "Homme":
        marge_broca = 0.10
        lorentz = (taille - 100) - (taille - 150) / 4
        notre = -75.78529 + 0.85456 * taille      # notre formule (modèle M3)
    else:
        marge_broca = 0.15
        lorentz = (taille - 100) - (taille - 150) / 2.5
        notre = -43.1349 + 0.61159 * taille

    imc = poids / (taille / 100) ** 2

    lignes = []
    for nom, ref, marge in [("Broca", broca, marge_broca),
                            ("Lorentz", lorentz, 0.15),
                            ("Creff", creff, 0.15)]:
        lignes.append({"Formule": nom,
                       "Poids normal (kg)": f"{ref:.1f}",
                       "Écart (kg)": f"{poids - ref:+.1f}",
                       "Diagnostic": diagnostic(poids, ref, marge)})

    lignes.append({"Formule": "IMC",
                   "Poids normal (kg)": f"IMC = {imc:.1f}",
                   "Écart (kg)": "-",
                   "Diagnostic": diagnostic_imc(imc)})

    lignes.append({"Formule": "Notre formule",
                   "Poids normal (kg)": f"{notre:.1f}",
                   "Écart (kg)": f"{poids - notre:+.1f}",
                   "Diagnostic": diagnostic(poids, notre, MARGE_NOTRE)})
    return lignes


def colorer(valeur):
    """Colore la case selon le diagnostic."""
    if valeur in COULEURS:
        return f"background-color: {COULEURS[valeur]}; color: white; font-weight: bold"
    return ""


def tableau_colore(df):
    """Applique les couleurs à la colonne Diagnostic (compatible anciennes versions de pandas)."""
    style = df.style
    appliquer = getattr(style, "map", None) or style.applymap
    return appliquer(colorer, subset=["Diagnostic"])


# Interface
st.title(" Diagnostic du poids")
st.caption("Outil d'aide au diagnostic")

onglet1, onglet2, onglet3 = st.tabs(["Diagnostic individuel", "Import de fichier", "Formules"])

# Onglet 1 : diagnostic individuel 
with onglet1:
    with st.form("formulaire"):
        sexe = st.radio("Sexe", ["Homme", "Femme"], horizontal=True)
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Âge (ans)", 15, 90, 21)
        taille = c2.number_input("Taille (cm)", 100, 230, 170)
        poids = c3.number_input("Poids (kg)", 20.0, 300.0, 65.0)
        valider = st.form_submit_button("Diagnostiquer", type="primary")

    if valider:
        # Avertissements : notre formule n'est valable que dans la zone étudiée
        taille_max = 195 if sexe == "Homme" else 185
        if taille < 160 or taille > taille_max:
            st.warning(f"Taille hors de la zone étudiée (160 à {taille_max} cm pour ce sexe) : "
                       "notre formule est moins fiable.")
        if age < 19 or age > 24:
            st.warning("Notre formule a été construite sur des étudiants de 19 à 24 ans.")

        lignes = calculer(sexe, age, taille, poids)
        df = pd.DataFrame(lignes)

        # Résultat principal (notre formule), en grand et en couleur
        diag_notre = lignes[-1]["Diagnostic"]
        st.markdown(
            f"<div style='background:{COULEURS[diag_notre]}; color:white; padding:14px; "
            f"border-radius:8px; text-align:center; font-size:22px;'>"
            f"Notre formule : <b>{diag_notre}</b></div>",
            unsafe_allow_html=True,
        )

        # Résultats détaillés
        st.subheader("Diagnostic selon chaque formule")
        st.table(tableau_colore(df.set_index("Formule")))

        # Les formules sont-elles d'accord ? (lien avec la question 1)
        diagnostics = list(df["Diagnostic"])
        if len(set(diagnostics)) == 1:
            st.success(f"Les 5 formules sont d'accord : {diagnostics[0]}.")
        else:
            resume = ", ".join(f"{diagnostics.count(d)} × {d}" for d in sorted(set(diagnostics)))
            st.warning(f"Les formules ne sont pas d'accord ({resume}).")


# Onglet 2 : import de fichier 
with onglet2:
    st.write("Votre fichier CSV ou Excel doit contenir 4 colonnes : "
             "**sexe** (H/F ou Homme/Femme), **age**, **taille**, **poids**.")
    fichier = st.file_uploader("Choisir un fichier", type=["csv", "xlsx"])

    if fichier is not None:
        if fichier.name.endswith(".csv"):
            donnees = pd.read_csv(fichier)
        else:
            donnees = pd.read_excel(fichier)
        donnees.columns = [c.strip().lower() for c in donnees.columns]

        manquantes = [c for c in ["sexe", "age", "taille", "poids"] if c not in donnees.columns]
        if manquantes:
            st.error(f"Colonne(s) manquante(s) : {', '.join(manquantes)}")
        else:
            resultats = []
            for _, ligne in donnees.iterrows():
                s = "Femme" if str(ligne["sexe"]).strip().lower().startswith("f") else "Homme"
                lignes = calculer(s, ligne["age"], ligne["taille"], ligne["poids"])
                resultat = {"sexe": s, "age": ligne["age"], "taille": ligne["taille"], "poids": ligne["poids"]}
                for l in lignes:
                    resultat[l["Formule"]] = l["Diagnostic"]
                resultats.append(resultat)
            res = pd.DataFrame(resultats)

            st.subheader("Résultats")
            st.dataframe(res)

            st.subheader("Nombre d'étudiants par diagnostic")
            formules = ["Broca", "Lorentz", "Creff", "IMC", "Notre formule"]
            synthese = pd.DataFrame({f: res[f].value_counts() for f in formules}).fillna(0).astype(int)
            st.table(synthese)

            st.download_button("Télécharger les résultats (CSV)",
                               res.to_csv(index=False).encode("utf-8"),
                               file_name="resultats_diagnostic.csv",
                               mime="text/csv")

# Onglet 3 : formules 
with onglet3:
    st.markdown("""
**Poids normal (taille en cm, âge en années)**

| Formule | Poids normal | Seuil de diagnostic |
|---|---|---|
| Broca | taille − 100 | ±10 % (homme), ±15 % (femme) |
| Lorentz | Homme : (taille − 100) − (taille − 150)/4<br>Femme : (taille − 100) − (taille − 150)/2,5 | ±15 % |
| Creff | (taille − 100) + 0,09 × âge | ±15 % |
| IMC | poids / taille² (en m) | < 18,5 maigreur ; > 25 surpoids |
| **Notre formule** | Homme : −75,785 + 0,8546 × taille<br>Femme : −43,135 + 0,6116 × taille | ±15 % |


""", unsafe_allow_html=True)
