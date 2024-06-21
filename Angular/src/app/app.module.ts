import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatExpansionModule } from '@angular/material/expansion';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { HttpClientModule } from '@angular/common/http';
import { LightboxModule } from 'ngx-lightbox';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { SocketIoModule, SocketIoConfig } from 'ngx-socket-io';
import { MessageDisplayComponent } from './message-display/message-display.component';
import { MessageService } from './message.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { FormsModule } from '@angular/forms'; // Import FormsModule

import { PrinterControlComponent } from './features/printer-control/printer-control.component';
import { LightControlComponent } from './features/light-control/light-control.component';
import { ComportControlComponent } from './features/comport-control/comport-control.component';
import { CameraControlComponent } from './features/camera-control/camera-control.component';

@NgModule({
  declarations: [
    AppComponent,
    MessageDisplayComponent,
    PrinterControlComponent,
    LightControlComponent,
    ComportControlComponent,
    CameraControlComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    AppRoutingModule,
    LightboxModule,
    MatProgressBarModule,
    MatSidenavModule,
    MatExpansionModule,
    MatButtonModule,
    MatExpansionModule,
    MatIconModule,
    FormsModule,
  ],
  providers: [MessageService], // Add the MessageService to providers
  bootstrap: [AppComponent]
  
})

export class AppModule { }


