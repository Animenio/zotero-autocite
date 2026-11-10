Attribute VB_Name = "ZoteroAutoCite_Word_05"
Option Explicit

' Pulsante opzionale Word (Windows) da aggiungere alla barra Accesso Rapido.
' Il documento aperto NON viene modificato. Una copia con data/ora viene creata.
' Non abilita automaticamente alcuna macro.
Public Sub Zoterizza_Documento()
    Dim picker As FileDialog
    Dim pythonScript As String
    Dim sourcePath As String
    Dim outputPath As String
    Dim cmd As String
    Dim rc As Long
    Dim suffix As String
    Dim flag As String
    Dim actionChoice As VbMsgBoxResult
    Dim sh As Object

    If Documents.Count = 0 Then
        MsgBox "Apri prima un documento Word.", vbExclamation
        Exit Sub
    End If
    If ActiveDocument.Path = "" Then
        MsgBox "Salva prima il documento come .docx.", vbExclamation
        Exit Sub
    End If
    sourcePath = ActiveDocument.FullName
    If LCase$(Right$(sourcePath, 5)) <> ".docx" Then
        MsgBox "E' necessario un documento .docx.", vbExclamation
        Exit Sub
    End If
    If InStr(1, sourcePath, "_Zoterizzato", vbTextCompare) > 0 Then
        MsgBox "Seleziona il manoscritto originale, non la copia convertita.", vbExclamation
        Exit Sub
    End If
    If Not ActiveDocument.Saved Then ActiveDocument.Save

    pythonScript = GetSetting("ZoteroAutoCite", "Paths", "PythonScript_05", "")
    If Len(pythonScript) = 0 Or Dir(pythonScript) = "" Then
        Set picker = Application.FileDialog(msoFileDialogFilePicker)
        With picker
            .Title = "Seleziona zotero_autocite.py della versione 0.5"
            .Filters.Clear
            .Filters.Add "Script Python", "*.py"
            .AllowMultiSelect = False
            If .Show <> -1 Then Exit Sub
            pythonScript = .SelectedItems(1)
        End With
        If LCase$(Right$(pythonScript, 18)) <> "zotero_autocite.py" Then
            If MsgBox("Il file scelto non si chiama zotero_autocite.py. Continuare?", vbYesNo + vbExclamation) <> vbYes Then Exit Sub
        End If
        SaveSetting "ZoteroAutoCite", "Paths", "PythonScript_05", pythonScript
    End If

    actionChoice = MsgBox("Importare gli articoli mancanti nella raccolta Zotero gia' configurata?" & vbCrLf & _
                    "SI = autorizza importazione; NO = solo collegamenti a fonti gia' presenti; ANNULLA = esci.", _
                    vbYesNoCancel + vbQuestion, "Zotero AutoCite")
    If actionChoice = vbCancel Then Exit Sub
    flag = ""
    If actionChoice = vbYes Then flag = " --auto-import"

    suffix = Format$(Now, "yyyymmdd_hhnnss")
    outputPath = Left$(sourcePath, Len(sourcePath) - 5) & "_Zoterizzato_" & suffix & ".docx"
    cmd = "cmd.exe /c py " & Chr$(34) & pythonScript & Chr$(34) & _
          " " & Chr$(34) & sourcePath & Chr$(34) & _
          " --output " & Chr$(34) & outputPath & Chr$(34) & flag
    Set sh = CreateObject("WScript.Shell")
    rc = sh.Run(cmd, 1, True)
    If rc <> 0 Or Dir(outputPath) = "" Then
        MsgBox "Conversione non riuscita. Controlla la finestra del comando e il log.", vbCritical
        Exit Sub
    End If
    Documents.Open FileName:=outputPath, ReadOnly:=False
    MsgBox "Copia creata. In Word seleziona Zotero > Refresh e controlla il LOG CSV.", vbInformation
End Sub
