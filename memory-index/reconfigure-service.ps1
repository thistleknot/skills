$nssm = "C:\Users\user\.pi\bin\nssm.exe"
$newPath = "C:\Users\user\.skills\memory-index\mem_server.py"
$newDir = "C:\Users\user\.skills\memory-index"

& $nssm stop mem-server 2>$null
Start-Sleep -Seconds 2
& $nssm set mem-server AppParameters $newPath
& $nssm set mem-server AppDirectory $newDir
& $nssm set mem-server AppEnvironmentExtra "PYTHONIOENCODING=utf-8" "PYTHONUTF8=1" "MEM_DIR=C:\Users\user\memory-bank" "HOME=C:\Users\user" "USERPROFILE=C:\Users\user"
Start-Sleep -Seconds 1
& $nssm start mem-server
Start-Sleep -Seconds 3
Get-Service mem-server | Format-List Name, Status
