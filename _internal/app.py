import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from parser import parse_turn, save, load_all
from tvp import analyze, analyze_html, movement_conditionals_html, conditional_healing_html
from combat import analyze_combat, analyze_combat_html
from obsidian_theme import apply_obsidian, show_banner, themed_chart

st.set_page_config(page_title="TF Analyzer 0.6.4 | Obsidian",page_icon="📖",layout="wide")
apply_obsidian()
show_banner()
uploads=st.file_uploader("Fordulófájlok feltöltése – HTML vagy MHTML (egyszerre több is)",type=["mhtml","mht","html","htm"],accept_multiple_files=True)
if uploads and st.button("Feltöltött fordulók feldolgozása",type="primary"):
    fresh=0; skipped=0; errors=[]
    progress=st.progress(0)
    for i,f in enumerate(uploads):
        try:
            parsed=parse_turn(f.getvalue(),f.name)
            if save(parsed): fresh+=1
            else: skipped+=1
        except Exception as exc: errors.append(f"{f.name}: {exc}")
        progress.progress((i+1)/len(uploads))
    st.success(f"Új fordulók: {fresh} • Már meglévők, HTML frissítve: {skipped} • Hibák: {len(errors)}")
    for e in errors: st.error(e)
turns=load_all()
if not turns:
    st.info("Tölts fel egy vagy több HTML- vagy MHTML-fordulót az elemzéshez.")
    st.stop()
characters=sorted({x["character"] for x in turns})
chosen=st.sidebar.selectbox("Karakter",characters)
turns=[x for x in turns if x["character"]==chosen]
st.sidebar.caption(f"Adatbázis: {len(turns)} forduló")
min_t=min(x["turn"] for x in turns if x["turn"] is not None) if any(x["turn"] is not None for x in turns) else 0
max_t=max(x["turn"] for x in turns if x["turn"] is not None) if any(x["turn"] is not None for x in turns) else 0
if min_t<max_t:
    lo,hi=st.sidebar.slider("Fordulótartomány",min_t,max_t,(min_t,max_t))
    turns=[x for x in turns if x["turn"] is not None and lo<=x["turn"]<=hi]
tabs=st.tabs(["Áttekintés","TVP","Harcok","Parancsok","Hibajelzések","Keresés","Adatminőség"])
with tabs[0]:
    a,b,c=st.columns(3)
    a.metric("Fordulók",len(turns))
    b.metric("Parancssorok",sum(len(x["commands"]) for x in turns))
    c.metric("TVP-jelzések",sum(len(analyze_html(x["_html"]) if x.get("_html") else analyze(x["text"])) for x in turns))
    st.dataframe(pd.DataFrame([{"Forduló":x["turn"],"Fájl":x["filename"],"Parancssorok":len(x["commands"]),
      "Szövegsorok":x["lines"],"Hibajelzések":len(x["failures"])} for x in turns]),hide_index=True,use_container_width=True)
with tabs[1]:
    st.subheader("TVP-mérleg és források – 0.6.4 (HTML + MHTML)")
    st.caption("A tvpkap és tvpkolt HTML-jelölésekből kiolvasott tételek; a sáfránykő és a sztázisrelikvia szöveges kivétel. Sáfránypor, pszi meditáció, moa spektroszkóp, időtorzítás, tudatpont átváltás és reverziós prizma: szövegminta alapján azonosított bevételi források. A TVP-kiadásokat a legközelebbi megelőző &lt;td width=250&gt; parancssor első szava alapján csoportosítjuk; a numerikus paraméterek nem képeznek külön kategóriát. A bizonytalan tételek ellenőrizendők.")
    rows=[{"Forduló":x["turn"],"Típus":r["kind"],"TVP":r["amount"],"Kategória":r["category"],
           "KP":r["kp"],"Parancs":r["command"],"Egyenleg":r["balance"],"Ellenőrzés":r["quality"],
           "Sor":r["line"],"Bizonyíték":r["evidence"],"Környezet":r.get("context",""),"Módszer":r.get("method","")}
          for x in turns for r in (analyze_html(x["_html"]) if x.get("_html") else analyze(x["text"]))]
    if rows:
        df=pd.DataFrame(rows)
        earned=df[df["Típus"]=="Bevétel"]["TVP"].sum()
        spent=-df[df["Típus"]=="Kiadás"]["TVP"].sum()
        c1,c2,c3=st.columns(3)
        c1.metric("Felismert TVP-bevétel",f"{earned:,.0f}")
        c2.metric("Felismert TVP-kiadás",f"{spent:,.0f}")
        c3.metric("Nettó TVP-változás",f"{earned-spent:+,.0f}")
        missing_tvp_html=sum(1 for x in turns if not x.get("_html"))
        if missing_tvp_html:
            st.error(f"{missing_tvp_html} forduló HTML-je hiányzik. Töltsd fel ismét az eredeti HTML- vagy MHTML-fájlokat; ezeknél csak a régi szöveges felismerés fut.")
        st.info("A TVP-változásokat HTML-jelölések alapján számoljuk, a sáfránykő kivételével. A nyitó egyenleg nem mindig ismert. A TVP-kiadás kategóriája a megelőző HTML-parancscella alapján történik; ha ilyen nincs, Ismeretlen marad. A 'Környezet' oszlop segít az ok ellenőrzésében.")
        gains=df[df["Típus"]=="Bevétel"]
        costs=df[df["Típus"]=="Kiadás"]
        if not gains.empty:
            st.plotly_chart(themed_chart(px.bar(gains.groupby("Kategória",as_index=False)["TVP"].sum(),x="Kategória",y="TVP",title="TVP-bevételek forrásonként")),use_container_width=True)
        if not costs.empty:
            summary=costs.assign(Költség=-costs["TVP"]).groupby("Kategória",as_index=False)["Költség"].sum().sort_values("Költség",ascending=False)
            st.plotly_chart(themed_chart(px.bar(summary,x="Kategória",y="Költség",title="TVP-kiadások parancskódonként (HTML)")),use_container_width=True)
        st.subheader("M parancs – mozgás és feltételes események")
        st.caption("A feltételes kutatás és mászás csak darabszámként jelenik meg. A játék nem jelzi külön a TVP-költségüket; az M parancs teljes költségét nem bontjuk meg és nem becsüljük.")
        movement_rows=[]
        for turn_data in turns:
            t_records=analyze_html(turn_data["_html"]) if turn_data.get("_html") else analyze(turn_data["text"])
            m_cost=-sum(r["amount"] for r in t_records if r["kind"]=="Kiadás" and r["category"]=="M")
            counts=movement_conditionals_html(turn_data["_html"]) if turn_data.get("_html") else None
            movement_rows.append({"Forduló":turn_data["turn"], "M összes TVP":m_cost,
                "Feltételes kutatás (db)":counts["Feltételes kutatás"] if counts else None,
                "Feltételes mászás (db)":counts["Feltételes mászás"] if counts else None})
        if movement_rows:
            movement_df=pd.DataFrame(movement_rows)
            m1,m2,m3=st.columns(3)
            m1.metric("M – összes TVP",f'{movement_df["M összes TVP"].sum():,.0f}')
            m2.metric("Feltételes kutatás",f'{movement_df["Feltételes kutatás (db)"].sum():,.0f} db')
            m3.metric("Feltételes mászás",f'{movement_df["Feltételes mászás (db)"].sum():,.0f} db')
            st.dataframe(movement_df,hide_index=True,use_container_width=True)
            st.download_button("M parancs és feltételes események – CSV",movement_df.to_csv(index=False).encode("utf-8-sig"),"m_felteteles_esemenyek.csv","text/csv")
            if movement_df["Feltételes kutatás (db)"].isna().any():
                st.warning("Egyes fordulók eredeti HTML-je hiányzik: a feltételes események darabszáma ezeknél nem ellenőrizhető.")
        st.subheader("Feltételes gyógyítások")
        st.caption("A feltételes gyógyítások kizárólag darabszámként szerepelnek, a TVP-költségüket nem becsüljük és nem különítjük el.")
        healing_rows=[{"Forduló":x["turn"],"Feltételes gyógyítás (db)":conditional_healing_html(x["_html"]) if x.get("_html") else None} for x in turns]
        healing_df=pd.DataFrame(healing_rows)
        st.metric("Feltételes gyógyítások összesen",f'{healing_df["Feltételes gyógyítás (db)"].sum():,.0f} db')
        st.dataframe(healing_df,hide_index=True,use_container_width=True)
        st.download_button("Feltételes gyógyítások – CSV",healing_df.to_csv(index=False).encode("utf-8-sig"),"felteteles_gyogyitasok.csv","text/csv")
        if healing_df["Feltételes gyógyítás (db)"].isna().any():
            st.warning("Egyes fordulók eredeti HTML-je hiányzik: ezeknél a gyógyítások száma nem ellenőrizhető.")
        st.subheader("Fordulónkénti összesítés")
        agg=df[df["Típus"].isin(["Bevétel","Kiadás"])].groupby(["Forduló","Típus"],as_index=False)["TVP"].sum()
        st.dataframe(agg,hide_index=True,use_container_width=True)
        st.subheader("Tételes események és eredeti bizonyíték")
        st.dataframe(df,hide_index=True,use_container_width=True)
        st.download_button("TVP-események letöltése CSV-ben",df.to_csv(index=False).encode("utf-8-sig"),"tvp_esemenyek.csv","text/csv")
        mismatches=df[df["Ellenőrzés"].astype(str).str.contains("egyenleg ellenőrizendő",case=False,na=False)]
        if len(mismatches): st.info(f"{len(mismatches)} TVP-egyenleg ellenőrzendő. A szövegkörnyezetből vizsgáld meg az eltérést.")
    else: st.info("Nem található TVP-esemény.")
with tabs[2]:
    st.subheader("⚔️ Harci statisztikák – 0.3")
    st.caption("A sebzés, gyógyulás és nettó ÉP a játék csata utáni összesítéséből származik. A harci körök és a kéz szerinti támadások becslések, csak egyértelmű mintázat esetén jelennek meg. Nincsenek automatikus Düh-javaslatok.")
    battles=[b for x in turns for b in (analyze_combat_html(x["_html"],x["text"],x["turn"]) if x.get("_html") else analyze_combat(x["text"],x["turn"]))]
    missing_html=sum(1 for x in turns if not x.get('_html'))
    if missing_html:
        st.error(f"{missing_html} fordulóhoz még nincs eltárolt HTML! Töltsd fel ismét az eredeti HTML- vagy MHTML-fájlokat. A program a már importált fordulók HTML-jét is elmenti, duplikálás nélkül.")
    if not battles:
        st.info("Nem találtam felismerhető csatastatisztikát a kiválasztott fordulókban.")
    else:
        df=pd.DataFrame(battles)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Feldolgozott csaták",len(df))
        c2.metric("Elszenvedett sebzés",f'{df["taken"].sum():,}')
        c3.metric("Gyógyulás",f'{df["healed"].sum():,}')
        c4.metric("Nettó ÉP-változás",f'{df["net"].sum():+,}')
        st.caption(f"HTML alapján (encf1) azonosított csaták: {int((df.get('name_source',pd.Series(dtype=str))=='encf1').sum())} / {len(df)}. Több encf1 egy csata előtt: ellenőrizhető az encf1_candidates oszlopban.")
        errors=df[~df["net_matches"]]
        if len(errors): st.warning(f"{len(errors)} csatában a játék nettó ÉP-értéke eltér a gyógyulás mínusz sebződés képlettől. Az eredeti értéket változatlanul mutatjuk.")
        summary=df.groupby("monster",as_index=False).agg(
            harcok=("taken","size"), atlag_sebzes=("taken","mean"),
            atlag_gyogyulas=("healed","mean"), atlag_netto=("net","mean"),
            max_sebzes=("taken","max"), osszes_sebzes=("taken","sum"),
            atlag_kor=("rounds_est","mean"),otkoros=("rounds_est",lambda s:int((s==5).sum())),
            atlag_tartalek=("reserve_est","mean"), atlag_tp=("xp","mean"))
        summary["otkoros_arany_%"]=(summary["otkoros"]/summary["harcok"]*100).round(1)
        summary=summary.rename(columns={"monster":"Szörny","harcok":"Harcok","atlag_sebzes":"Átl. kapott sebzés",
            "atlag_gyogyulas":"Átl. gyógyulás","atlag_netto":"Átl. nettó ÉP","max_sebzes":"Legnagyobb sebzés",
            "osszes_sebzes":"Összes sebzés","atlag_kor":"Becsült átl. kör","otkoros":"Becsült 5 körös",
            "atlag_tartalek":"Becsült támadási tartalék","atlag_tp":"Átl. TP","otkoros_arany_%":"Becsült 5 körös %"})
        st.markdown("#### Szörnyenkénti összehasonlítás")
        st.dataframe(summary.sort_values("Átl. kapott sebzés",ascending=False),hide_index=True,use_container_width=True)
        st.download_button("Szörnyenkénti statisztika CSV",summary.to_csv(index=False).encode("utf-8-sig"),"tf_szornyek.csv","text/csv")
        rank=summary.sort_values("Átl. kapott sebzés",ascending=False).head(20)
        st.plotly_chart(themed_chart(px.bar(rank,x="Szörny",y="Átl. kapott sebzés",title="Legnagyobb átlagos sebzést okozó szörnyek")),use_container_width=True)
        rank=summary.sort_values("Átl. nettó ÉP").head(20)
        st.plotly_chart(themed_chart(px.bar(rank,x="Szörny",y="Átl. nettó ÉP",title="Legrosszabb átlagos nettó ÉP-változás")),use_container_width=True)
        st.markdown("#### Egy szörny harcainak története")
        monster=st.selectbox("Szörny kiválasztása",sorted(df["monster"].unique()))
        selected=df[df["monster"]==monster].sort_values("turn")
        st.dataframe(selected[["turn","taken","healed","net","dealt","xp","rounds_est","last_right","last_left","max_right","max_left","reserve_est","line","evidence","attack_evidence"]].rename(columns={"turn":"Forduló","taken":"Sebződés","healed":"Gyógyulás","net":"Nettó ÉP","dealt":"Okozott sebzés","xp":"TP","rounds_est":"Becsült körök","last_right":"Utolsó jobb","last_left":"Utolsó bal","max_right":"Max. jobb","max_left":"Max. bal","reserve_est":"Becsült tartalék","line":"Sor","evidence":"Eredeti csatastatisztika","attack_evidence":"Támadások forrása"}),hide_index=True,use_container_width=True)
        st.markdown("#### Összes csata, ellenőrizhető forrással")
        st.dataframe(df,hide_index=True,use_container_width=True)
        st.download_button("Összes csata CSV",df.to_csv(index=False).encode("utf-8-sig"),"tf_harcok.csv","text/csv")
        st.info("A kör- és támadásszámok csak akkor jelennek meg, ha a szövegből egyértelműen párosíthatók a támadási csoportok. A hiányzó adat nem nulla. A kézi és távolsági támadások elkülönítése még ellenőrzendő, ezért a becslések nem alkalmasak automatikus döntésekre.")
with tabs[3]:
    rows=[{"Forduló":x["turn"],"Parancs":c["command"],"Paraméterek":c["arguments"],"Sor":c["line"],"Környezet":c["context"]}
          for x in turns for c in x["commands"]]
    if rows:
        df=pd.DataFrame(rows)
        st.plotly_chart(themed_chart(px.bar(df.groupby("Parancs").size().reset_index(name="Darab"),x="Parancs",y="Darab",title="Felismert parancssorok")),use_container_width=True)
        st.dataframe(df,hide_index=True,use_container_width=True)
        st.download_button("Parancsok CSV",df.to_csv(index=False).encode("utf-8-sig"),"parancsok.csv","text/csv")
with tabs[4]:
    rows=[{"Forduló":x["turn"],"Sor":f["line"],"Részlet":f["text"]} for x in turns for f in x["failures"]]
    st.caption("Kizárólag a HTML <span class=hiba> jelöléseiből gyűjtött hibajelzések.")
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else: st.info("Nem található hibajelzés.")
with tabs[5]:
    query=st.text_input("Keresés az összes importált fordulóban")
    if query:
        hits=[]
        for x in turns:
            for i,line in enumerate(x["text"].splitlines()):
                if query.casefold() in line.casefold():
                    hits.append({"Forduló":x["turn"],"Sor":i+1,"Találat":line[:500]})
                    if len(hits)>=1000: break
            if len(hits)>=1000: break
        st.caption(f"{len(hits)} találat (legfeljebb 1000 jelenik meg)")
        if hits: st.dataframe(pd.DataFrame(hits),hide_index=True,use_container_width=True)
with tabs[6]:
    st.markdown("""**Feldolgozási állapot:** 0.6.4 (Obsidian) – HTML-alapú TVP-könyvelés, a 0.3.3 harci modullal.
- A HTML-szöveg és az alapvető parancsok feldolgozása működik.
- A TVP-kapás `tvpkap`, a TVP-költés `tvpkolt` jelölésből, a sáfránykő és a sztázisrelikvia szöveges kivételeiből kerül kiolvasásra. A bevételi forrás szövegkörnyezeti becslés; a kiadási parancskód az előző td[width=250] HTML-cellából származik.
- A csaták sebzés- és gyógyulásösszesítése kiolvasható; a kör- és támadásszámok óvatos becslések.
- A Hibajelzések fül kizárólag a HTML span.hiba elemeit gyűjti.
- A feltételes gyógyítások darabszáma külön látható, TVP-becslés nélkül.
- A sáfránypor és a moa spektroszkóp felismerése a megbeszélt szövegváltozatokat használja.
- Az eredeti HTML tömörítve megmarad az adatbázisban az újra feltöltött MHTML-fordulóknál; a régi fordulókat egyszer újra kell feltölteni a HTML pótlásához.""")
