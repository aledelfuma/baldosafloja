def page_personas_full(df_personas, df_ap, df_seg, centro, usuario):
    st.subheader("👥 Legajo Digital")
    df_centro = personas_for_centro(df_personas, centro)
    
    if not df_centro.empty:
        df_centro["timestamp_dt"] = pd.to_datetime(df_centro["timestamp"], errors="coerce")
        df_centro = df_centro.sort_values("timestamp", ascending=True).groupby("nombre").tail(1)
    
    nombres = sorted(df_centro["nombre"].unique()) if not df_centro.empty else []

    col_sel, col_act = st.columns([3, 1])
    seleccion = col_sel.selectbox("🔍 Buscar a una persona en el padrón:", [""] + nombres, help="Escriba aquí para buscar por nombre")
    
    if not seleccion:
        st.markdown("<div class='alert-box alert-info'>ℹ️ Utilice el buscador para abrir una ficha individual, o revise el listado histórico debajo.</div>", unsafe_allow_html=True)
        st.markdown(f"### Listado Histórico ({len(nombres)} personas)")
        
        with st.expander("📥 Descargar Padrón o Ver Tabla", expanded=False):
            if not df_centro.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_centro.to_excel(writer, sheet_name='Personas', index=False)
                st.download_button("Descargar Excel de Padrón", buffer, f"padron_{centro}.xlsx", "application/vnd.ms-excel", use_container_width=True)
                
                solo_activos = st.checkbox("Mostrar Solo activos", value=True)
                df_show = df_centro.copy()
                if solo_activos: df_show = df_show[df_show["activo"].astype(str).str.upper() == "SI"]
                
                cols_to_show = ["nombre", "dni", "fecha_nacimiento", "telefono", "activo", "etiquetas", "contacto_emergencia"]
                for c in cols_to_show:
                    if c not in df_show.columns: df_show[c] = ""
                st.dataframe(df_show[cols_to_show].sort_values("nombre"), use_container_width=True, hide_index=True)
        return

    datos_persona = df_centro[df_centro["nombre"] == seleccion].iloc[0]
    
    tags_str = str(datos_persona.get("etiquetas", ""))
    tags_html = ""
    if tags_str and tags_str.lower() != "nan":
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for t in tags: tags_html += f"<span class='tag-badge'>{t}</span>"

    telefono = str(datos_persona.get("telefono", ""))
    wa_btn_html = ""
    if telefono and telefono.lower() != "nan" and format_wa_number(telefono):
        wa_btn_html = f"<div style='margin-top:10px;'><a href='https://wa.me/{format_wa_number(telefono)}' target='_blank' class='btn-wa'>💬 Contactar por WhatsApp</a></div>"
        
    estado_badge = "🟢 SOCIO/A ACTIVO" if str(datos_persona.get("activo")).upper() != "NO" else "🔴 INACTIVO"
    
    import urllib.parse
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(seleccion)}&backgroundColor=004e7b&textColor=ffffff"

    # Limpieza de DNI y Edad para evitar "nan" visual
    dni_val = str(datos_persona.get('dni', '')).strip()
    if dni_val.lower() == 'nan' or not dni_val:
        dni_val = "No registrado"
        
    nac_val = str(datos_persona.get('fecha_nacimiento', '')).strip()
    if nac_val.lower() == 'nan' or not nac_val:
        nacimiento_mostrar = "No registrada"
    else:
        nacimiento_mostrar = f"{nac_val} ({calculate_age(nac_val)} años)"

    # 🚨 FIX HTML: Pegado a la izquierda sin sangría para que Streamlit no lo haga código
    html_carnet = f"""
<div style="display: flex; flex-direction: column; gap: 20px;">
<div class="id-card" style="margin-bottom:0px;">
<div style="display:flex; justify-content: space-between; align-items:flex-start; margin-bottom: 5px;">
<div class="id-title">HOGAR DE CRISTO • {centro.upper()}</div>
<span style="font-weight:800; background: rgba(255,255,255,0.25); padding: 5px 12px; border-radius: 12px; font-size: 0.70rem; letter-spacing:1px;">
{estado_badge}
</span>
</div>
<div style="display:flex; gap: 20px; align-items: center; margin-bottom: 20px;">
<img src="{avatar_url}" style="width: 70px; height: 70px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.8); box-shadow: 0 4px 10px rgba(0,0,0,0.1);"/>
<div class="id-name" style="margin-bottom:0;">{seleccion}</div>
</div>
<div class="id-data-row">
<div class="id-data-col">
<span class="id-label">DNI / Documento</span>
<span class="id-value">{dni_val}</span>
</div>
<div class="id-data-col">
<span class="id-label">Nacimiento (Edad)</span>
<span class="id-value">{nacimiento_mostrar}</span>
</div>
</div>
<div class="tag-container">
{tags_html}
</div>
</div>
</div>
<br>
"""
    st.markdown(html_carnet, unsafe_allow_html=True)
    
    c_info, c_bitacora = st.columns([1.2, 1.8], gap="medium")
    
    with c_info:
        st.markdown("### 📞 Datos de Contacto")
        
        domicilio_val = str(datos_persona.get('domicilio', '')).strip()
        if domicilio_val.lower() == 'nan' or not domicilio_val: domicilio_val = 'No registrado'
        
        st.markdown(f"""
        <div class="profile-card" style="padding: 15px;">
            <div style="font-size: 0.8rem; color:var(--text-gray); text-transform:uppercase; font-weight:700;">🏠 Domicilio Actual</div>
            <div style="font-weight: 600; font-size:1.1rem; color:var(--text-dark); margin-top:2px;">{domicilio_val}</div>
        </div>
        """, unsafe_allow_html=True)
        
        tel_val = str(datos_persona.get('telefono', '')).strip()
        if tel_val.lower() == 'nan' or not tel_val: tel_val = 'No registrado'
        
        st.markdown(f"""
        <div class="profile-card" style="padding: 15px; border-left: 4px solid var(--primary);">
            <div style="font-size: 0.8rem; color:var(--text-gray); text-transform:uppercase; font-weight:700;">📱 Celular Principal</div>
            <div style="font-weight: 600; font-size:1.2rem; color:var(--text-dark); margin-top:2px;">{tel_val}</div>
            {wa_btn_html}
        </div>
        """, unsafe_allow_html=True)
        
        emergencia = str(datos_persona.get('contacto_emergencia', '')).strip()
        if emergencia and emergencia.lower() != 'nan':
            st.markdown(f"""
            <div class="profile-card" style="padding: 15px; background-color: #FEF2F2; border: 1px solid #FEE2E2; border-left: 4px solid #DF2020;">
                <div style="font-size: 0.8rem; color:#991B1B; text-transform:uppercase; font-weight:800;">🚨 Contacto de Emergencia</div>
                <div style="font-weight: 700; font-size:1.0rem; color:#7F1D1D; margin-top:2px;">{emergencia}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("🚨 No posee contacto de emergencia cargado.")
            
        notas_str = str(datos_persona.get('notas', '')).strip()
        if notas_str and notas_str.lower() != 'nan':
            st.info(f"**Notas Fijas (Alergias/Contexto):**\n\n{notas_str}")

        with st.expander("✏️ Editar Ficha de la Persona"):
            with st.form("edit_persona"):
                dni = st.text_input("DNI", value=datos_persona.get("dni", ""))
                tel = st.text_input("Teléfono", value=datos_persona.get("telefono", ""))
                contacto_em = st.text_input("🚨 Contacto Emergencia", value=datos_persona.get("contacto_emergencia", ""))
                nac = st.text_input("Fecha Nac. (DD/MM/AAAA)", value=datos_persona.get("fecha_nacimiento", ""))
                dom = st.text_input("Domicilio", value=datos_persona.get("domicilio", ""))
                etiquetas = st.text_input("Etiquetas (Separadas por coma)", value=datos_persona.get("etiquetas", ""), help="Ej: Diabético, Medicación, Pensionado")
                notas_fija = st.text_area("Notas Fijas (Alergias, Condiciones crónicas)", value=datos_persona.get("notas", ""))
                activo_chk = st.checkbox("Sigue Activo (Si se desmarca, no saldrá en el padrón)", value=(str(datos_persona.get("activo")).upper() != "NO"))
                
                if st.form_submit_button("💾 Guardar Cambios Permanentes", use_container_width=True):
                    nuevo_estado = "SI" if activo_chk else "NO"
                    upsert_persona(df_personas, seleccion, centro, usuario, dni=dni, telefono=tel, fecha_nacimiento=nac, domicilio=dom, notas=notas_fija, activo=nuevo_estado, contacto_emergencia=contacto_em, etiquetas=etiquetas)
                    st.success("¡Ficha actualizada!")
                    time.sleep(1)
                    st.cache_data.clear(); st.rerun()
        
    with c_bitacora:
        st.markdown("### 📖 Bitácora Reciente")
        st.caption("Carga aquí cualquier seguimiento médico, trabajador social, psicólogo, o charla importante.")
        
        with st.expander("➕ Escribir en la Bitácora", expanded=False):
            with st.form("new_seg"):
                fecha_seg = st.date_input("Fecha de Consulta", value=get_today_ar())
                cat = st.selectbox("Categoría / Área", CATEGORIAS_SEGUIMIENTO)
                obs = st.text_area("Detalle de lo hablado o sucedido...")
                if st.form_submit_button("📝 Guardar Registro", use_container_width=True):
                    if len(obs) > 5:
                        append_seguimiento(str(fecha_seg), centro, seleccion, cat, obs, usuario)
                        st.success("Guardado correctamente")
                        time.sleep(1)
                        st.cache_data.clear(); st.rerun()
                    else:
                        st.error("Por favor escriba más detalles.")
        
        if not df_seg.empty:
            mis_notas = df_seg[(df_seg["nombre"]==seleccion) & (df_seg["centro"]==centro)].copy()
            if not mis_notas.empty:
                mis_notas["fecha_dt"] = pd.to_datetime(mis_notas["fecha"], errors="coerce")
                mis_notas = mis_notas.sort_values("fecha_dt", ascending=False)
                
                st.markdown("<br>", unsafe_allow_html=True)
                for _, note in mis_notas.iterrows():
                    cat = str(note['categoria']).lower()
                    icon = "🩺" if "salud" in cat else "📝" if "trámite" in cat else "🫂" if 'escucha' in cat else "🚨" if 'crisis' in cat else "📌"
                    color_left = "#DC2626" if "crisis" in cat else SECONDARY
                    
                    st.markdown(f"""
                    <div style="background-color: var(--surface-color); padding:15px; border-radius:var(--radius-sm); margin-bottom:12px; border-left: 5px solid {color_left}; box-shadow: var(--shadow-soft);">
                        <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom:8px; margin-bottom:8px;">
                            <strong style="color:var(--primary); font-size:1.05rem;">{icon} {note['categoria']}</strong>
                            <div style="text-align:right;">
                                <div style="color:var(--text-gray); font-size:0.75rem; font-weight:700;">{note['fecha']}</div>
                                <div style="color:var(--text-gray); font-size:0.65rem; padding-top:2px;">Por: {str(note.get('usuario', ''))}</div>
                            </div>
                        </div>
                        <div style="font-size:0.95rem; color:var(--text-dark); line-height:1.5;">{note['observacion']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("Sin registros en la bitácora aún.")
