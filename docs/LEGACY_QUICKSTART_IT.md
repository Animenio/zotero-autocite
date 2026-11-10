# Zotero AutoCite Desktop 0.5 — avvio rapido (Windows)

## Prima di iniziare

Questa versione riutilizza **senza rinumerazione** il catalogo già creato da AutoCite 0.4.2. La vecchia versione resta utilizzabile: non serve eliminarla.

1. Apri Zotero Desktop, con l'accesso locale attivo: **Impostazioni > Avanzate > Consenti alle altre applicazioni su questo computer di comunicare con Zotero**.
2. Estrai **l'intero file ZIP** in una nuova cartella, ad esempio `Documenti\AutoCite_0.5`. Non eseguire lo script dentro lo ZIP compresso.
3. **Fai doppio clic su `AutoCite_Desktop.pyw`**. Su Windows con Python 3.10+ installato in modo standard, dovrebbe comparire la finestra grafica. Non serve aprire il Prompt dei comandi per ogni utilizzo.
4. Se il file `.pyw` non parte, nella cartella fai clic nella barra degli indirizzi, scrivi `cmd` e premi Invio. Esegui una sola volta `py -m pip install -r requirements.txt`, poi verifica Python grafico con `py -m tkinter` e apri l'app con `pyw AutoCite_Desktop.pyw`. Le dipendenze erano già state installate per l'MVP precedente.

## Uso in quattro schede

### 1. Cerca articolo

- Incolla il **DOI**, per esempio `10.1016/j.techfore.2016.08.019`, e premi **Cerca**. Il DOI è preferibile perché identifica direttamente la fonte.
- Oppure digita un titolo/autore, seleziona il risultato OpenAlex corretto e premi **Verifica articolo selezionato**.
- Controlla titolo, autori, anno, DOI e stato di verifica. Premi **Registra e copia codice**: il sistema riutilizza il codice già assegnato se la fonte esiste nel catalogo.
- La registrazione nel catalogo **non** crea subito un elemento in Zotero: questo avviene nella fase di conversione Word, solo con l'importazione abilitata.

### 2. Catalogo e codici

- Cerca per titolo o DOI fra gli articoli presenti nel registro locale, seleziona una riga e premi **Copia codice selezionato**.
- **Esporta CSV** crea un archivio Excel-compatibile contenente codici e identificativi.
- Il database rimane in `%APPDATA%\ZoteroAutoCite\catalogo.sqlite3` e non viene spostato.

### 3. Zotero e raccolte

- Premi **Verifica Zotero / Aggiorna raccolte**.
- Scegli **AutoCite TEST** (oppure la raccolta desiderata) dal menu a discesa, poi **Salva la raccolta selezionata**.
- L'app memorizza l'identificativo della raccolta in `%APPDATA%\ZoteroAutoCite\settings.json` e lo verifica rispetto all'istanza Zotero.

### 4. Converti Word

1. In Word scrivi le citazioni, ad esempio `Il fenomeno è stato studiato [[Z:06937]].`, e inserisci `[[ZBIB]]` nel paragrafo in cui vuoi la bibliografia.
2. Salva il file come `.docx` e **chiudi Word**.
3. Nella scheda **Converti Word**, premi **Sfoglia…** e seleziona il documento **originale**.
4. Lascia attiva l'opzione di importazione **solo se** desideri che gli articoli assenti siano aggiunti a Zotero nella raccolta scelta. L'app chiede conferma prima di procedere e Zotero può chiedere l'autorizzazione alla scrittura.
5. Premi **Zoterizza documento**. Il file originale resta intatto; il programma crea un nuovo documento `..._Zoterizzato.docx` e un LOG CSV/JSON. Se esiste già un file generato, utilizza `_Zoterizzato_2.docx`, ecc., senza sovrascrivere.
6. Premi **Apri Word generato** e in Word seleziona **Zotero > Refresh**. Controlla bibliografia, citazioni e LOG.

> **Importante**: la ricerca esterna non invia il contenuto del documento Word a OpenAlex/Crossref. Solo i termini di ricerca, i DOI e gli identificativi richiesti sono trasmessi online. Il catalogo SQLite resta sul tuo computer.

## Pulsante Word opzionale

La cartella include `ZoteroAutoCite_Word_05.bas`, un modulo VBA per Microsoft Word Desktop **Windows**. È facoltativo: l'app grafica funziona senza macro.

1. In Word vai su **File > Opzioni > Personalizzazione barra multifunzione** e abilita **Sviluppo**.
2. Premi **Alt+F11**. Seleziona il progetto **Normal** e scegli **File > Importa file**: importa `ZoteroAutoCite_Word_05.bas` in un progetto attendibile.
3. Chiudi l'editor VBA, vai su **File > Opzioni > Barra di accesso rapido**. In **Scegli comandi da: Macro**, aggiungi `Zoterizza_Documento` alla barra.
4. Premi quel pulsante con un `.docx` originale aperto. Alla prima esecuzione seleziona il file `zotero_autocite.py` **della versione 0.5**. La macro propone di importare o non importare le fonti mancanti, crea una copia con data/ora, apre il risultato e chiede di usare Zotero > Refresh.

**Sicurezza**: non attivare tutte le macro indiscriminatamente. Verifica il contenuto del file `.bas`; la macro invoca Python ed è eseguita solo se autorizzata dalle impostazioni di Office. Non installiamo automaticamente macro, plug-in o componenti aggiuntivi.

## Verifiche e limiti

- AutoCite 0.5 utilizza il **motore 0.4.2 già collaudato** nel flusso Word + Zotero. La nuova interfaccia è stata verificata con test automatici e una sessione grafica virtuale, ma **non ancora collaudata sul tuo Windows**.
- Il recupero online richiede una connessione Internet; le operazioni sulla libreria e conversione di fonti già presenti richiedono Zotero aperto, ma non inviano il manoscritto online.
- I codici anonimi senza DOI richiedono un ID OpenAlex selezionato esplicitamente. I record con metadati insufficienti, incongruenti o ambigui sono bloccati o riportati nel LOG, mai collegati arbitrariamente.
- La versione 0.5 **non implementa ancora** la conversione automatica di citazioni narrative o multicitazioni in un solo campo Zotero; è un obiettivo distinto della versione successiva.
- `AutoCite_Desktop.pyw` è un'app Python grafica, **non un eseguibile .exe indipendente**. `Tkinter` è incluso nelle installazioni standard di Python per Windows.
- Se OpenAlex richiede una API key per la quota disponibile, configura la variabile d'ambiente `OPENALEX_API_KEY` in Windows e riavvia l'app. Non incollare le chiavi in documenti Word.

### Controllo test automatici (facoltativo)

Nella cartella, `py -m unittest -v` esegue la suite senza contattare Zotero reale o i database bibliografici reali.
