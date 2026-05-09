#!/usr/bin/env pwsh
# Lanzador para PowerShell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
python sysmonitorpro.py @args
