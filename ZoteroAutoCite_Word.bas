Attribute VB_Name = "ZoteroAutoCite_Word"
Option Explicit

' Importare come modulo VBA in Word (Windows), opzionale.
' Non modifica mai il file originale. Richiede Python e Zotero in esecuzione.
Public Sub Zotero_AutoCite_Converti()
    Dim f As FileDialog
    Dim scriptPath As String
    Dim sourcePath As String
    Dim targetPath As String
    Dim shell As Object
    Dim commandLine As String
    Dim returnCode As Long

    If ActiveDocument.Path = "" Then
        MsgBox "Salva prima il documento Word come .docx.", vbExclamation
        Exit Sub
    End If
    If LCase$(Right$(ActiveDocument.FullName, 5)) <> ".docx" Then
        MsgBox "Il convertitore richiede un documento .docx.", vbExclamation
        Exit Sub
    End If
    If Not ActiveDocument.Saved Then ActiveDocument.Save

    ' La prima volta, seleziona zotero_autocite.py dal pacchetto.
    scriptPath = GetSetting("ZoteroAutoCite", "Paths", "PythonScript", "")
    If Len(scriptPath) = 0 Or Dir(scriptPath) = "" Then
        Set f = Application.FileDialog(msoFileDialogFilePicker)
        With f
            .Title = "Seleziona zotero_autocite.py"
            .Filters.Clear
            .Filters.Add "Python", "*.py"
            .AllowMultiSelect = False
            If .Show <> -1 Then Exit Sub
            scriptPath = .SelectedItems(1)
        End With
        SaveSetting "ZoteroAutoCite", "Paths", "PythonScript", scriptPath
    End If

    sourcePath = ActiveDocument.FullName
    targetPath = Left$(sourcePath, Len(sourcePath) - 5) & "_Zoterizzato.docx"
    If Dir(targetPath) <> "" Then
        If MsgBox("Sovrascrivere la COPIA convertita esistente?" & vbCrLf & targetPath, vbYesNo + vbQuestion) <> vbYes Then Exit Sub
    End If

    Set shell = CreateObject("WScript.Shell")
    commandLine = "cmd.exe /c py " & Chr$(34) & scriptPath & Chr$(34) & " " & Chr$(34) & sourcePath & Chr$(34)
    returnCode = shell.Run(commandLine, 1, True)
    If returnCode <> 0 Or Dir(targetPath) = "" Then
        MsgBox "Conversione non completata. Controlla gli errori della finestra del comando.", vbCritical
        Exit Sub
    End If
    Documents.Open FileName:=targetPath, ReadOnly:=False
    MsgBox "Copia aperta. Verifica il LOG CSV, poi usa Zotero > Refresh per aggiornare citazioni e bibliografia.", vbInformation
End Sub
