const { app, BrowserWindow, nativeImage, shell } = require("electron");
const path = require("path");
const url = require("url");
const os=require('os');
const{dialog}=require('electron');
const { spawn } = require('child_process');
const { webContents } = require('electron')



let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({ 
    width: 800, 
    height: 600, 
    autoHideMenuBar: true,
  icon:  ('src/assets/EagleEye.png'),
  webPreferences: {
    webSecurity: false,
    nodeIntegration: true,
    allowRunningInsecureContent: true,
    contextIsolation: false,
    enableRemoteModule: true,
    devTools: true
  },
});

mainWindow.center();

mainWindow.removeMenu();
mainWindow.webContents.openDevTools();


  mainWindow.loadURL(
    url.format({
      pathname: path.join(__dirname, 'dist', 'new2-granda-ai', 'index.html'),
      protocol: "file:",
      slashes: true,
    
    })
    
    
    );


  mainWindow.on("closed", () => {
    const { exec } = require("child_process");
    exec("taskkill /f /t /im EagleAI_main.exe", (err, stdout, stderr) => {
       if (err) { 
         console.log(err) 
         return; 
        } 
        console.log(`stdout: ${stdout}`); 
        console.log(`stderr: ${stderr}`);});
    mainWindow = null;
  });
}


app.on("ready",  () => {
//    const backendPath = ( 'backend/EagleAI_main.exe' );
//const backendProcess = spawn(backendPath);

//backendProcess.stdout.on('data', (data) => {
  //console.log(`EagleAI_main.exe output: ${data}`);
//});

//backendProcess.stderr.on('data', (data) => {
 // console.error(`EagleAI_main.exe error: ${data}`);
//});

//backendProcess.on('close', (code) => {
 // console.log(`EagleAI_main.exe exited with code ${code}`);
//});
    createWindow();

  

});
app.on("activate", () => {
  if (mainWindow === null) {
  //  const backendPath = ( 'backend/EagleAI_main.exe' );
//const backendProcess = spawn(backendPath);

//backendProcess.stdout.on('data', (data) => {
 // console.log(`EagleAI_main.exe output: ${data}`);
//});

//backendProcess.stderr.on('data', (data) => {
  //console.error(`EagleAI_main.exe error: ${data}`);
//});

//backendProcess.on('close', (code) => {
  //console.log(`EagleAI_main.exe exited with code ${code}`);
//});
    createWindow();

  }

  ipc.on('open-file-dialog', function(event){
    if (os.platform()==='win64')
    {
        dialog.showOpenDialog({
        properties:['openFile']
    }, function(files){
        if (files){
            event.sender.send('selected-file', files[0]);
        }})}})})
