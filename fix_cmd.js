const fs = require('fs');
const path = require('path');

const cmdCode = (name) => {
    return `@ECHO off
GOTO start
:find_dp0
SET dp0=%~dp0
EXIT /b
:start
SETLOCAL
CALL :find_dp0

IF EXIST "%dp0%\\node.exe" (
    SET "_prog=%dp0%\\node.exe"
) ELSE (
    SET "_prog=node"
    SET PATHEXT=%PATHEXT:;.JS;=;%
)

endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  "%dp0%\\node_modules\\${name}\\cli.js" %*`;
}

let appdata = process.env.APPDATA || (process.platform == 'darwin' ? process.env.HOME + '/Library/Preferences' : process.env.HOME + "/.local/share");
appdata = path.join(appdata, 'npm');
const cmd_path = path.join(appdata, `${process.env.npm_package_name}.cmd`);

if (process.env.npm_config_global === 'true') {
    try {
        const cmd_code = cmdCode(process.env.npm_package_name);
        fs.writeFileSync(cmd_path, cmd_code);
    } catch (err) {
        console.error(err);
        throw err;
    }
}