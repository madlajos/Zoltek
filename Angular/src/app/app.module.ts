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
import { FormsModule } from '@angular/forms';
import { MatCommonModule } from '@angular/material/core';

import { TurntableControlComponent } from './features/turntable-control/turntable-control.component';
import { ComportControlComponent } from './features/comport-control/comport-control.component';
import { CameraControlComponent } from './features/camera-control/camera-control.component';
import { ImageViewerComponent } from './features/image-viewer/image-viewer.component';
import { SharedService } from './shared.service';
import { ControlPanelComponent } from './features/control-panel/control-panel.component';

@NgModule({
  declarations: [
    AppComponent,
    MessageDisplayComponent,
    TurntableControlComponent,
    ComportControlComponent,
    CameraControlComponent,
    ImageViewerComponent,
    ControlPanelComponent,
  ],
  imports: [
    MatCommonModule,
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    AppRoutingModule,
    LightboxModule,
    MatProgressBarModule,
    MatSidenavModule,
    MatExpansionModule,
    MatButtonModule,
    MatIconModule,
    FormsModule,
  ],
  providers: [SharedService, MessageService],
  bootstrap: [AppComponent]
})
export class AppModule {}
