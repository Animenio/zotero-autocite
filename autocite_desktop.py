"""Zotero AutoCite Desktop 0.5 - interfaccia grafica locale (tkinter)."""
from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext

import autocite_desktop_core as core

FONT = 'Segoe UI'


class DesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Zotero AutoCite 0.5  |  Desktop')
        self.geometry('1070x830')
        self.minsize(830, 740)
        self.configure(bg='#F6F8FC')
        self._jobs = queue.Queue()
        self._busy = False
        self._results = []
        self._verified_meta = None
        self._collection_opts = []
        self._server_id = None
        self._last_converted = None
        self._configure_style()
        self._build()
        self._load_settings_label()
        self.after(100, self._drain)
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _configure_style(self):
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('TFrame', background='#F6F8FC')
        style.configure('Panel.TFrame', background='#FFFFFF')
        style.configure('TLabel', background='#F6F8FC', foreground='#17243B', font=(FONT,10))
        style.configure('Panel.TLabel', background='#FFFFFF', foreground='#17243B', font=(FONT,10))
        style.configure('Title.TLabel', font=(FONT,21,'bold'), background='#F6F8FC',foreground='#14223A')
        style.configure('Sub.TLabel', font=(FONT,10), background='#F6F8FC', foreground='#526176')
        style.configure('Section.TLabel', font=(FONT,12,'bold'),background='#F6F8FC',foreground='#203450')
        style.configure('TButton', font=(FONT,10), padding=(11,8))
        style.configure('Primary.TButton', background='#155FCC',foreground='white',font=(FONT,10,'bold'))
        style.map('Primary.TButton',background=[('active','#0E4EA9'),('disabled','#9EB9E2')],foreground=[('disabled','#FFFFFF')])
        style.configure('TNotebook',background='#F6F8FC',borderwidth=0)
        style.configure('TNotebook.Tab',font=(FONT,10),padding=(16,10),background='#E8EDF5')
        style.map('TNotebook.Tab',background=[('selected','#FFFFFF')])
        style.configure('Treeview',font=(FONT,9),rowheight=29)
        style.configure('Treeview.Heading',font=(FONT,9,'bold'))
        style.configure('TEntry',padding=7)
        style.configure('TCombobox',padding=5)

    def _build(self):
        header=ttk.Frame(self,padding=(24,20,24,10)); header.pack(fill='x')
        ttk.Label(header,text='Zotero AutoCite',style='Title.TLabel').pack(anchor='w')
        ttk.Label(header,text='Dalla ricerca bibliografica alle citazioni dinamiche Word — senza Prompt dei comandi',style='Sub.TLabel').pack(anchor='w',pady=(4,0))
        self.notebook=ttk.Notebook(self); self.notebook.pack(fill='both',expand=True,padx=22,pady=(6,8))
        self.search_tab=ttk.Frame(self.notebook,padding=17)
        self.catalog_tab=ttk.Frame(self.notebook,padding=17)
        self.word_tab=ttk.Frame(self.notebook,padding=17)
        self.settings_tab=ttk.Frame(self.notebook,padding=17)
        self.notebook.add(self.search_tab,text='  Cerca articolo  ')
        self.notebook.add(self.catalog_tab,text='  Catalogo e codici  ')
        self.notebook.add(self.word_tab,text='  Converti Word  ')
        self.notebook.add(self.settings_tab,text='  Zotero e raccolte  ')
        self._build_search(); self._build_catalog(); self._build_word(); self._build_settings()
        status=ttk.Frame(self,padding=(22,8,22,13)); status.pack(fill='x')
        self.status_var=tk.StringVar(value='Pronto. Apri Zotero Desktop prima di importare o convertire.')
        ttk.Label(status,textvariable=self.status_var,style='Sub.TLabel').pack(side='left',fill='x',expand=True)
        self.progress=ttk.Progressbar(status,length=140,mode='indeterminate'); self.progress.pack(side='right')

    def _build_search(self):
        f=self.search_tab
        ttk.Label(f,text='Ricerca DOI-first, oppure titolo / autore',style='Section.TLabel').pack(anchor='w',pady=(0,10))
        bar=ttk.Frame(f); bar.pack(fill='x')
        self.search_var=tk.StringVar()
        search=ttk.Entry(bar,textvariable=self.search_var,font=(FONT,11))
        search.pack(side='left',fill='x',expand=True,padx=(0,9)); search.bind('<Return>',lambda _:self._search())
        ttk.Button(bar,text='Cerca',style='Primary.TButton',command=self._search).pack(side='right')
        ttk.Label(f,text='DOI esatto: 10.1016/j.techfore.2016.08.019  •  Oppure un titolo scientifico',style='Sub.TLabel').pack(anchor='w',pady=(7,13))
        container=ttk.Frame(f); container.pack(fill='both',expand=True)
        cols=('anno','autore','titolo','doi')
        tree=ttk.Treeview(container,columns=cols,show='headings',selectmode='browse',height=6)
        tree.heading('anno',text='Anno'); tree.column('anno',width=60,stretch=False)
        tree.heading('autore',text='Primo autore'); tree.column('autore',width=160,stretch=False)
        tree.heading('titolo',text='Titolo'); tree.column('titolo',width=370,stretch=True)
        tree.heading('doi',text='DOI'); tree.column('doi',width=220,stretch=False)
        tree.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(container,orient='vertical',command=tree.yview); sb.pack(side='right',fill='y'); tree.configure(yscrollcommand=sb.set)
        self.search_tree=tree; self.search_tree.bind('<<TreeviewSelect>>',lambda _:self._clear_preview())
        actions=ttk.Frame(f); actions.pack(fill='x',pady=(12,9))
        ttk.Button(actions,text='Verifica articolo selezionato',command=self._verify).pack(side='left')
        self.verification_state=tk.StringVar(value='Scegli un risultato e verifica la corrispondenza bibliografica.')
        ttk.Label(actions,textvariable=self.verification_state,style='Sub.TLabel').pack(side='left',padx=14)
        ttk.Label(f,text='Anteprima della fonte verificata',style='Section.TLabel').pack(anchor='w',pady=(4,6))
        self.source_preview=tk.Text(f,height=4,wrap='word',font=(FONT,10),bg='#FFFFFF',fg='#17243B',borderwidth=1,relief='solid',state='disabled')
        self.source_preview.pack(fill='x')
        footer=ttk.Frame(f);footer.pack(fill='x',pady=(12,0))
        self.register_btn=ttk.Button(footer,text='Registra e copia codice',style='Primary.TButton',command=self._register_source,state='disabled');self.register_btn.pack(side='left')
        self.new_alias_var=tk.StringVar(value='')
        ttk.Label(footer,textvariable=self.new_alias_var,style='Sub.TLabel').pack(side='left',padx=15)

    def _build_catalog(self):
        f=self.catalog_tab
        ttk.Label(f,text='I codici già assegnati rimangono invariati',style='Section.TLabel').pack(anchor='w',pady=(0,10))
        bar=ttk.Frame(f);bar.pack(fill='x')
        self.catalog_query=tk.StringVar()
        entry=ttk.Entry(bar,textvariable=self.catalog_query);entry.pack(side='left',fill='x',expand=True,padx=(0,8));entry.bind('<Return>',lambda _:self._refresh_catalog())
        ttk.Button(bar,text='Cerca nel catalogo',command=self._refresh_catalog).pack(side='left',padx=(0,8))
        ttk.Button(bar,text='Esporta CSV',command=self._export_catalog).pack(side='left')
        frame=ttk.Frame(f);frame.pack(fill='both',expand=True,pady=(12,6))
        cols=('codice','anno','titolo','doi','zotero')
        t=ttk.Treeview(frame,columns=cols,show='headings',selectmode='browse')
        for col,title,width,stretch in [('codice','Codice',120,False),('anno','Anno',65,False),('titolo','Titolo',385,True),('doi','DOI',230,False),('zotero','Zotero',85,False)]:
            t.heading(col,text=title);t.column(col,width=width,stretch=stretch)
        t.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(frame,orient='vertical',command=t.yview);sb.pack(side='right',fill='y');t.configure(yscrollcommand=sb.set)
        self.catalog_tree=t
        foot=ttk.Frame(f);foot.pack(fill='x',pady=(6,0))
        ttk.Button(foot,text='Copia codice selezionato',style='Primary.TButton',command=self._copy_catalog_alias).pack(side='left')
        self.catalog_count=tk.StringVar(value='Usa Cerca per caricare i riferimenti locali.')
        ttk.Label(foot,textvariable=self.catalog_count,style='Sub.TLabel').pack(side='left',padx=15)

    def _build_word(self):
        f=self.word_tab
        ttk.Label(f,text='Converti un manoscritto in citazioni Zotero dinamiche',style='Section.TLabel').pack(anchor='w',pady=(0,10))
        b=ttk.Frame(f);b.pack(fill='x')
        self.word_path=tk.StringVar()
        ttk.Entry(b,textvariable=self.word_path).pack(side='left',fill='x',expand=True,padx=(0,8))
        ttk.Button(b,text='Sfoglia…',command=self._browse_word).pack(side='right')
        ttk.Label(f,text='Il documento originale non sarà modificato. Verrà creata una nuova copia con suffisso _Zoterizzato.',style='Sub.TLabel').pack(anchor='w',pady=(8,16))
        self.import_var=tk.BooleanVar(value=True)
        ttk.Checkbutton(f,text='Importa in Zotero i codici non ancora presenti, nella raccolta selezionata',variable=self.import_var).pack(anchor='w')
        ttk.Label(f,text='Per le importazioni Zotero può chiederti esplicitamente un’autorizzazione alla scrittura.',style='Sub.TLabel').pack(anchor='w',pady=(4,14))
        line=ttk.Frame(f);line.pack(fill='x')
        ttk.Label(line,text='Stile iniziale:',style='TLabel').pack(side='left',padx=(0,10))
        self.style_var=tk.StringVar(value='apa')
        ttk.Combobox(line,textvariable=self.style_var,values=('apa','harvard1','chicago-author-date'),width=25,state='readonly').pack(side='left')
        ttk.Button(line,text='Zoterizza documento',style='Primary.TButton',command=self._convert).pack(side='right')
        ttk.Label(f,text='Report conversione',style='Section.TLabel').pack(anchor='w',pady=(20,8))
        self.output_text=scrolledtext.ScrolledText(f,height=12,wrap='word',font=('Consolas',10),bg='#FFFFFF',fg='#243146',borderwidth=1,relief='solid')
        self.output_text.pack(fill='both',expand=True)
        self.output_text.insert('end','Scegli un documento Word originale e premi «Zoterizza documento».\n')
        self.output_text.configure(state='disabled')
        actions=ttk.Frame(f);actions.pack(fill='x',pady=(10,0))
        self.open_word_btn=ttk.Button(actions,text='Apri Word generato',command=lambda:self._open_last('output'),state='disabled');self.open_word_btn.pack(side='left')
        self.open_log_btn=ttk.Button(actions,text='Apri log CSV',command=lambda:self._open_last('csv'),state='disabled');self.open_log_btn.pack(side='left',padx=(8,0))
        ttk.Label(actions,text='Dopo l’apertura in Word: Zotero → Refresh.',style='Sub.TLabel').pack(side='right')

    def _build_settings(self):
        f=self.settings_tab
        ttk.Label(f,text='Connessione locale e raccolta di destinazione',style='Section.TLabel').pack(anchor='w',pady=(0,12))
        self.zotero_state=tk.StringVar(value='Zotero: da verificare')
        ttk.Label(f,textvariable=self.zotero_state).pack(anchor='w',pady=(0,14))
        ttk.Button(f,text='Verifica Zotero / Aggiorna raccolte',style='Primary.TButton',command=self._get_collections).pack(anchor='w',pady=(0,16))
        ttk.Label(f,text='Raccolta per le nuove importazioni:',style='Section.TLabel').pack(anchor='w',pady=(0,8))
        self.collection_var=tk.StringVar()
        self.collection_combo=ttk.Combobox(f,textvariable=self.collection_var,state='readonly',width=80)
        self.collection_combo.pack(anchor='w',fill='x',pady=(0,12))
        ttk.Button(f,text='Salva la raccolta selezionata',command=self._save_collection).pack(anchor='w')
        self.saved_collection_var=tk.StringVar(value='')
        ttk.Label(f,textvariable=self.saved_collection_var,style='Sub.TLabel').pack(anchor='w',pady=(17,0))
        sep=ttk.Separator(f,orient='horizontal');sep.pack(fill='x',pady=22)
        ttk.Label(f,text='Sicurezza e dati',style='Section.TLabel').pack(anchor='w')
        for msg in ('• Il catalogo dei codici è conservato sul tuo computer in %APPDATA%\\ZoteroAutoCite.',
                    '• Le ricerche inviano titolo o DOI a OpenAlex e Crossref, non il contenuto del manoscritto.',
                    '• Nessun dato viene scritto nel database Zotero tramite SQL.',
                    '• Le importazioni avvengono soltanto se le abiliti e autorizzi Zotero.',
                    '• È richiesto Zotero Desktop 10 o successivo per le operazioni di scrittura.'):
            ttk.Label(f,text=msg,style='Sub.TLabel').pack(anchor='w',pady=(9,0))

    def _load_settings_label(self):
        try:
            data=core.configured_collection()
            name=data.get('collection_name') if data else None
            self.saved_collection_var.set('Raccolta configurata: '+str(name) if name else 'Nessuna raccolta ancora configurata.')
        except Exception as exc:
            self.saved_collection_var.set('Configurazione da verificare: '+str(exc))

    def _work(self, label, fn, success):
        if self._busy:
            messagebox.showinfo('Operazione in corso','Attendi che termini l’operazione già avviata.');return
        self._busy=True
        self.status_var.set(label);self.progress.start(9)
        def runner():
            try:
                result=fn()
                self._jobs.put(('ok', result, success))
            except Exception as exc:
                self._jobs.put(('error', str(exc), None))
        threading.Thread(target=runner,daemon=True).start()

    def _drain(self):
        try:
            while True:
                outcome, value, callback=self._jobs.get_nowait()
                self._busy=False;self.progress.stop()
                if outcome=='error':
                    self.status_var.set('Operazione non riuscita: '+value[:140])
                    messagebox.showerror('AutoCite — errore',value)
                else:
                    try:
                        callback(value)
                    except Exception as exc:
                        messagebox.showerror('Errore interfaccia',str(exc))
                    self.status_var.set('Operazione completata.')
        except queue.Empty:
            pass
        self.after(120,self._drain)

    def _clear_preview(self):
        self._verified_meta=None
        self.register_btn.configure(state='disabled')
        self.verification_state.set('Verifica la fonte prima di salvarla.')
        self.new_alias_var.set('')
        self._set_preview('')

    def _set_preview(self,value):
        self.source_preview.configure(state='normal');self.source_preview.delete('1.0','end');self.source_preview.insert('1.0',value);self.source_preview.configure(state='disabled')

    def _search(self):
        query=self.search_var.get().strip()
        self._clear_preview()
        if not query:
            messagebox.showwarning('Ricerca','Inserisci un DOI, titolo o autore.');return
        def success(items):
            self._results=items
            for iid in self.search_tree.get_children():self.search_tree.delete(iid)
            for i,row in enumerate(items):
                first=row.get('first_author') or ', '.join(a.get('family','') for a in (row.get('authors') or [])[:2])
                self.search_tree.insert('', 'end', iid=str(i), values=(row.get('year',''), first,
                     row.get('title',''), row.get('doi','')))
            self.verification_state.set(f'{len(items)} risultato/i. Seleziona la pubblicazione corretta.')
            if len(items)==1:self.search_tree.selection_set('0')
        self._work('Interrogo OpenAlex e Crossref…',lambda:core.search_publications(query),success)

    def _verify(self):
        selected=self.search_tree.selection()
        if not selected:
            messagebox.showinfo('Verifica','Seleziona un articolo nell’elenco.');return
        row=self._results[int(selected[0])]
        def success(meta):
            self._verified_meta=meta
            authors=', '.join((a.get('given','')+' '+a.get('family','')).strip() for a in meta['authors'][:4]);authors+= ' et al.' if len(meta['authors'])>4 else ''
            self._set_preview(f"{meta['title']} ({meta['year']})\n{authors}\nDOI: {meta.get('DOI') or 'assente'}  |  OpenAlex: {meta.get('openalex_id') or '—'}\nVerifica: {meta.get('verification','—')}")
            self.verification_state.set('Fonte verificata. Conferma il salvataggio per ottenere il codice.')
            self.register_btn.configure(state='normal')
        self._work('Verifico identità e metadati bibliografici…',lambda:core.verify_result(row),success)

    def _register_source(self):
        meta=self._verified_meta
        if not meta:return
        if meta.get('verification')=='OPENALEX_ONLY':
            msg='Questa fonte non ha DOI ed è verificata soltanto tramite OpenAlex. Confermi i metadati mostrati?'
        else:
            msg='Registrare questa pubblicazione nel catalogo locale e ottenere il codice breve?'
        if not messagebox.askyesno('Conferma registrazione',msg):return
        def success(data):
            alias,entry=data
            self.clipboard_clear();self.clipboard_append(alias)
            self.new_alias_var.set('Codice copiato: '+alias)
            messagebox.showinfo('Codice AutoCite',f"Codice copiato negli appunti:\n{alias}\n\n{entry['title']}\n\nInseriscilo nel documento Word.")
        self._work('Salvo codice bibliografico…',lambda:core.save_verified_meta(meta),success)

    def _refresh_catalog(self):
        def success(rows):
            for iid in self.catalog_tree.get_children():self.catalog_tree.delete(iid)
            for i,row in enumerate(rows):
                self.catalog_tree.insert('','end',iid=str(i),values=(f"[[Z:{row['id']:05d}]]",row['year'],row['title'],row['doi'],row['zotero_key']))
            self.catalog_count.set(f'{len(rows)} risultati (max 250 mostrati).')
        self._work('Leggo il catalogo locale…',lambda:core.list_catalog(self.catalog_query.get(),250),success)

    def _copy_catalog_alias(self):
        sel=self.catalog_tree.selection()
        if not sel:
            messagebox.showinfo('Catalogo','Seleziona un codice da copiare.');return
        code=self.catalog_tree.item(sel[0],'values')[0]
        self.clipboard_clear();self.clipboard_append(code)
        self.catalog_count.set('Copiato negli appunti: '+code)

    def _export_catalog(self):
        filename=filedialog.asksaveasfilename(title='Esporta catalogo AutoCite',defaultextension='.csv',filetypes=[('CSV Excel','*.csv')],initialfile='Catalogo_AutoCite.csv')
        if not filename:return
        self._work('Esporto catalogo in CSV…',lambda:core.export_catalog_csv(filename),lambda result:messagebox.showinfo('Esportazione','File creato:\n'+result))

    def _browse_word(self):
        result=filedialog.askopenfilename(title='Seleziona documento Word originale',filetypes=[('Documento Word','*.docx')])
        if result:self.word_path.set(result)

    def _log_word(self,value):
        self.output_text.configure(state='normal');self.output_text.delete('1.0','end');self.output_text.insert('end',value);self.output_text.configure(state='disabled')

    def _convert(self):
        doc=self.word_path.get().strip()
        try:
            core.planned_output_path(doc)
        except Exception as exc:
            messagebox.showerror('Documento non valido',str(exc));return
        auto=self.import_var.get()
        if auto:
            conf=core.configured_collection()
            if not conf or not conf.get('collection_key'):
                messagebox.showerror('Raccolta mancante','Apri «Zotero e raccolte» e scegli la raccolta destinazione prima di importare.');return
            if not messagebox.askyesno('Conferma importazione Zotero',
                 f"Le citazioni assenti potranno essere IMPORTATE o aggiunte alla raccolta «{conf.get('collection_name')}».\n\nIl documento originale non sarà modificato. Procedere?"):
                return
        self._log_word('Elaborazione in corso…\n')
        def success(res):
            self._last_converted=res
            display=('Documento creato: '+res['output']+'\n'
                  +'Libreria Zotero: '+str(res['indexed'])+' voci indicizzate\n\n'
                  +'Esiti:\n')
            for name,amount in res['counts'].items():display+=f'  {name}: {amount}\n'
            display+='\nLOG CSV: '+res['csv']+'\nRiepilogo JSON: '+res['json']+'\n\nApri Word e usa Zotero → Refresh.'
            self._log_word(display)
            self.open_word_btn.configure(state='normal');self.open_log_btn.configure(state='normal')
            messagebox.showinfo('Conversione terminata','Copia Word e report generati.\nControlla gli esiti e premi Zotero → Refresh.')
        self._work('Elaboro il documento e i collegamenti bibliografici…',lambda:core.convert_word(doc,auto_import=auto,style=self.style_var.get()),success)

    def _open_last(self,what):
        path=(self._last_converted or {}).get(what)
        if not path or not Path(path).exists():
            messagebox.showerror('File','File non trovato.');return
        if os.name=='nt':os.startfile(path)
        else:messagebox.showinfo('Percorso',path)

    def _get_collections(self):
        def success(data):
            self._server_id, self._collection_opts=data
            values=[f"{row['name']}   [{row['key']}]" for row in self._collection_opts]
            self.collection_combo.configure(values=values)
            saved=core.configured_collection() or {}
            index=next((i for i,r in enumerate(self._collection_opts) if r['key']==saved.get('collection_key')),None)
            if index is not None:self.collection_combo.current(index)
            elif values:self.collection_combo.current(0)
            self.zotero_state.set(f'Zotero collegato · {len(values)} raccolte personali rilevate')
        self._work('Leggo le raccolte Zotero…',core.zotero_collection_choices,success)

    def _save_collection(self):
        index=self.collection_combo.current()
        if index<0 or self._server_id is None or index>=len(self._collection_opts):
            messagebox.showwarning('Raccolta','Premi «Verifica Zotero / Aggiorna raccolte» e seleziona una raccolta.');return
        row=self._collection_opts[index]
        if not messagebox.askyesno('Conferma raccolta',f"Usare «{row['name']}» come destinazione degli articoli importati?"):
            return
        def success(res):
            self._load_settings_label()
            messagebox.showinfo('Raccolta configurata',f"Salvata: {res['collection_name']} [{res['collection_key']}]")
        self._work('Salvo la raccolta di destinazione…',lambda:core.save_collection_choice(self._server_id,row['key'],row['name'],self._collection_opts),success)

    def _close(self):
        if self._busy:
            messagebox.showwarning('Operazione in corso','L’operazione è ancora in corso. Per evitare interruzioni durante l’importazione Zotero, chiudi al termine.');return
        self.destroy()


def main():
    app=DesktopApp();app.mainloop()


if __name__=='__main__':
    main()
