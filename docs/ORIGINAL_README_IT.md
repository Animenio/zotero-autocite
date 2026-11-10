# Zotero AutoCite Desktop 0.5

**Avvio consigliato:** doppio clic su `AutoCite_Desktop.pyw`. Leggi `AVVIO_RAPIDO_0.5.md` per la procedura grafica e il pulsante Word facoltativo.

La v0.5 aggiunge una interfaccia grafica a Zotero AutoCite 0.4.2 senza modificare il motore di conversione Word collaudato. Il catalogo `%APPDATA%\ZoteroAutoCite\catalogo.sqlite3` è condiviso con le versioni precedenti, senza migrazione.

---

# Documentazione del motore 0.4.2 (conservata per compatibilità)

# Zotero AutoCite 0.4.2 BETA — OpenAlex + Crossref + Zotero + Word

**Software gratuito e locale.** Ricerca accademica OpenAlex, verifica DOI con Crossref, alias `[[Z:00001]]` in SQLite, importazione in una **raccolta Zotero scelta dall'utente**, conversione in campi Word dinamici e bibliografia Zotero.

## Correzione 0.4.2 — errore HTTP 404 /items/new

- Il test reale 0.4.1 ha mostrato che `GET /api/items/new?itemType=...` risponde **404 No endpoint found** su alcune installazioni Zotero. L'importazione falliva *prima* di chiedere autorizzazione alla scrittura.
- AutoCite 0.4.2 non richiede più il template dall'endpoint locale. Prepara un oggetto bibliografico limitato ai campi attesi per tipo e invia l'array a `POST /api/users/0/items`, che è l'endpoint ufficiale per creare item. Il dialogo di autorizzazione locale Zotero rimane obbligatorio.
- In caso di fallimento, ripetere lo stesso codice più volte nel manoscritto non provoca ripetuti tentativi di scrittura durante la stessa conversione: l'errore viene riportato per ogni marcatore nel LOG, ma la scrittura è tentata una sola volta.
- Nel pacchetto è presente `Test_AutoCite_042_Frey_Osborne_PULITO.docx`: contiene *esclusivamente* due marcatori `[[Z:06937]]`, nessun alias dimostrativo destinato ad altri articoli, più `[[ZBIB]]`. Non serve modificare il documento.
- **I codici esistenti e le impostazioni restano in `%APPDATA%\ZoteroAutoCite`**, senza migrazioni. Non eliminare il catalogo.
- Questa correzione è verificata tramite test automatici offline; la scrittura su Zotero Desktop reale deve ancora essere collaudata.

### Retest rapido

1. Chiudi Microsoft Word, lascia Zotero Desktop aperto. Apri la raccolta `AutoCite TEST`.
2. Estrai questo ZIP in una cartella nuova. Non serve reinstallare Python né registrare nuovamente l'articolo su OpenAlex; il codice `[[Z:06937]]` rimane invariato.
3. Trascina `Test_AutoCite_042_Frey_Osborne_PULITO.docx` su `Avvia_AutoCite.bat`.
4. Quando Zotero presenta la richiesta di autorizzazione scrittura per `Zotero AutoCite`, autorizza solo dopo aver verificato l'app. Se il riferimento è già presente nella libreria, il programma dovrebbe riutilizzarlo senza crearne un altro.
5. Il risultato atteso nel LOG è `CONVERTITA: 2` e `BIBLIOGRAFIA_INSERITA: 1`; l'eventuale riga `IMPORTAZIONE_FALLITA` ora riporterà un errore differente, utile per la diagnosi.
6. Apri il `.docx` trasformato, premi Zotero → Refresh e controlla la bibliografia e la raccolta `AutoCite TEST`.

## Stato e precauzioni

- La conversione Word (derivata da AutoCite 0.1.2) è stata collaudata su Word e Zotero dall'utente. Il modulo OpenAlex/Crossref della 0.4 è stato **testato automaticamente con risposte simulate**, ma **non ancora su un Zotero reale con Internet**. È una BETA: usare documenti di prova e una raccolta Zotero di test.
- Il programma **non modifica il database interno di Zotero** né l'originale Word. Crea nuove voci Zotero **solo quando il documento contiene un codice selezionato e `--auto-import` è attivo**, è stata configurata una raccolta e si autorizza la scrittura nell'app Zotero 10+.
- Non scarica PDF o testi integrali. OpenAlex e Crossref ricevono online i termini di ricerca e DOI richiesti; il contenuto dei file Word **non viene inviato** a quei servizi.
- I record senza DOI sono importabili solo quando scelti tramite ID OpenAlex e completi di titolo, anno e autori. La verifica Crossref per essi non è possibile: controllare manualmente i metadati.
- In caso di DOI duplicato, titolo+anno già presenti, discrepanza fra fonti, problemi di connessione o autorizzazione, la conversione viene sospesa per quella fonte e registrata nel log. Non si creano riferimenti per semplice somiglianza.

## Requisiti

1. Windows con Word Desktop e plugin Zotero Word.
2. Zotero Desktop **10 o superiore**, aperto e con **Impostazioni → Avanzate → Consenti alle altre applicazioni su questo computer di comunicare con Zotero** attivo.
3. Python 3.10+, verificabile da `py --version`.
4. Aprire questa cartella, cliccare sulla barra indirizzi di Esplora File, digitare `cmd` e premere Invio. Poi eseguire:

   `py -m pip install -r requirements.txt`

5. OpenAlex è interrogabile senza API key per uso limitato. Per quote gratuite più ampie, creare una **API key gratuita** su https://openalex.org/ e, nel Prompt della cartella digitare `set OPENALEX_API_KEY=LA_TUA_CHIAVE` e **nella stessa finestra** avviare `Cerca_Articolo.bat`. Il comando `set` non vale per altre finestre aperte separatamente. La chiave è facoltativa e non viene salvata dall'app.

## Primo test raccomandato (una sola nuova pubblicazione)

**1. Crea una raccolta di prova in Zotero** denominata `AutoCite TEST` nella **libreria personale**. Non usare la raccolta di lavoro prima del collaudo.

**2. Esegui `Sincronizza_Catalogo.bat`.** AutoCite legge la libreria e assegna alias, senza scrivere in Zotero. Mantiene i codici già assegnati dalla 0.3. Il database si trova in `%APPDATA%\ZoteroAutoCite\catalogo.sqlite3`.

**3. Esegui `Configura_Raccolta.bat`.** Scegli dall'elenco `AutoCite TEST`. Il programma ricorderà la chiave della raccolta (e l'ID dell'istanza Zotero) nel file `%APPDATA%\ZoteroAutoCite\settings.json`.

**4. Esegui `Cerca_Articolo.bat`.** Inserisci **preferibilmente il DOI**, ad esempio `10.1016/j.techfore.2016.08.019` (accettati anche `doi:...` e `https://doi.org/...`). Con il DOI, AutoCite:
   - recupera direttamente il record OpenAlex senza la lista di risultati;
   - verifica l'identità bibliografica confrontando OpenAlex e Crossref;
   - se il DOI non esiste in OpenAlex (404), prova il recupero esatto da Crossref;
   - chiede conferma prima di assegnare il codice breve, senza scrivere ancora in Zotero;
   - conserva il codice breve esistente se la fonte è già registrata.

   **In alternativa**, inserisci titolo o autore. AutoCite mostra risultati OpenAlex (titolo, anno, autore, DOI, ID W...), quindi:
   - scegli il risultato con un numero (0 = annulla);
   - AutoCite recupera il record completo e, se contiene un DOI, verifica DOI/titolo/anno/primo autore usando Crossref;
   - se la verifica è incoerente **non salva** la fonte;
   - controlla i metadati mostrati e rispondi `s` alla domanda di registrazione;
   - ottieni un codice, ad esempio `[[Z:00421]]` (esempio, il tuo codice sarà diverso).

**5. Apri un Word vuoto e scrivi**, sostituendo con il codice veramente ottenuto:

    Questo studio è rilevante per il dibattito scientifico [[Z:00421]].

    Bibliografia

    [[ZBIB]]

Salva come `Prova_AutoCite_04.docx` e chiudi Word.

**6. Trascina il file Word su `Avvia_AutoCite.bat`.** Solo se la fonte non esiste nella tua libreria, AutoCite proverà a crearla nella raccolta selezionata. Zotero mostrerà una finestra di autorizzazione alla scrittura: controlla il nome dell'app e autorizza soltanto se vuoi procedere. Se la fonte esiste già, il programma può aggiungerla alla raccolta scelta senza duplicarla.

**7. Apri il file `Prova_AutoCite_04_Zoterizzato.docx`** e premi `Zotero → Refresh` in Word. Prova `Add/Edit Citation` su una citazione per confermare che è collegata. Controlla i file `_LOG.csv` e `_riepilogo.json`.

**8. Verifica in Zotero** che la voce sia nella raccolta `AutoCite TEST` e che il DOI, gli autori e il titolo siano corretti. **Non fare una prova massiva finché questo punto non è superato.**

## Altri comandi

| File o comando | Funzione |
|---|---|
| `Trova_Codice.bat` | Cerca i codici già assegnati, senza API online |
| `Aggiungi_OpenAlex_ID.bat` | Aggiunge un record specifico usando il suo identificativo `W...` |
| `Cerca_su_Crossref.bat` | Alternativa di ricerca direttamente su Crossref |
| `Aggiungi_DOI.bat` | Scorciatoia legacy: salva un DOI solo tramite Crossref, senza il confronto OpenAlex |
| `Esporta_Catalogo_Excel.bat` | Esporta CSV dei codici con identificativi, fonte e verifica |
| `py autocite_catalog.py list "ESG"` | Elenca gli alias presenti che corrispondono al titolo/DOI |
| `py autocite_catalog.py add-openalex W2741809807` | Aggiunge il record per ID OpenAlex e verifica Crossref se ha DOI |
| `py autocite_catalog.py import-bib "bibliografia.bib"` | Importa record con DOI da BibTeX nel registro |
| `py zotero_autocite.py "paper.docx"` | Convertitore senza scrittura Zotero (esce `NON_IN_ZOTERO` per gli assenti) |
| `py zotero_autocite.py "paper.docx" --auto-import` | Converte e importa nella raccolta scelta gli assenti |
| `py -m unittest -v` | Esegue i test automatici su dati fittizi |

## Architettura e identità

- **OpenAlex** è la fonte principale per discovery, non un mirror locale di tutto il database scientifico.
- **Crossref** è fonte di verifica dei metadati per i DOI registrati presso Crossref. Un DOI valido di un'altra agenzia potrebbe non essere riconosciuto: il programma segnala l'errore, non inventa una corrispondenza.
- **Catalogo SQLite**: `id` numerico persistente, `openalex_id` `W...`, DOI opzionale, titolo, autori, anno, provenienza, metadati, server/library/item-key Zotero. I codici non vengono riassegnati.
- **Zotero**: prima ricerca per DOI o chiave già collegata; se non trova DOI, verifica potenziali duplicati per titolo/anno; se l'importazione è autorizzata, usa `POST /api/users/0/items` con la chiave temporanea concessa da Zotero. Non importa mai automaticamente nella libreria di gruppo.
- **Word**: solo i marcatori espliciti vengono convertiti. Un marcatore sconosciuto o ambiguo rimane visibile nel documento e compare nel log.

### Compatibilità con la versione precedente

La 0.4 utilizza lo **stesso percorso dati della 0.3**. Al primo avvio migra il catalogo aggiungendo l'identificativo OpenAlex **senza cambiare i codici** e crea un backup `catalogo_backup_pre_0.4.sqlite3`. Non eliminare o spostare `%APPDATA%\ZoteroAutoCite` quando aggiorni il programma.

I formati precedenti restano validi:

- `{(Rossi, 2023); doi:10.xxxx/yyy}`
- `{(Rossi, 2023); key:ABCD1234}`
- `[[ZCITE:doi:10.xxxx/yyy]]`
- `[[Z:00001]]`
- `[[ZBIB]]`

Limiti ancora presenti: citazioni multiple in un unico campo, citazioni narrative, paragrafi con campi Word esistenti e marcatori in note, intestazioni, piè di pagina, commenti e hyperlink. Usare copie dei manoscritti.

### Fonti ufficiali

- OpenAlex API: https://help.openalex.org/api/
- OpenAlex autenticazione: https://help.openalex.org/api/authentication/
- Crossref REST: https://www.crossref.org/documentation/retrieve-metadata/rest-api
- Zotero API locale: https://www.zotero.org/support/dev/web_api/v3/local_api
- Zotero API scrittura: https://www.zotero.org/support/dev/web_api/v3/write_requests
