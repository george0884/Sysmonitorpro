#!/usr/bin/env pwsh
# Lanzador para PowerShell (el programa está en la carpeta padre de scripts/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $scriptDir)
python sysmonitorpro.py @args
