import { Component, ViewChild, ChangeDetectorRef, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Lightbox } from 'ngx-lightbox';
import { MatSidenav } from '@angular/material/sidenav';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { FormsModule } from '@angular/forms';

// Import standalone components
import { ImageViewerComponent } from './features/image-viewer/image-viewer.component';
import { ControlPanelComponent } from './features/control-panel/control-panel.component';
import { TurntableControlComponent } from './features/turntable-control/turntable-control.component';
import { ComportControlComponent } from './features/comport-control/comport-control.component';
import { CameraControlComponent } from './features/camera-control/camera-control.component';
import { ResultsTableComponent } from './features/results-table/results-table.component';
import { ErrorPopupListComponent } from './components/error-popup-list/error-popup-list.component';
import { BarcodeScannerControlComponent } from './features/barcode-scanner-control/barcode-scanner-control.component';
import { LoginPopupComponent } from './components/login-popup/login-popup.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    MatSidenavModule, 
    MatButtonModule, 
    MatIconModule, 
    MatExpansionModule,
    FormsModule,

    // Standalone components
    ImageViewerComponent,
    ControlPanelComponent,
    TurntableControlComponent,
    ComportControlComponent,
    CameraControlComponent,
    ResultsTableComponent,
    ErrorPopupListComponent,
    BarcodeScannerControlComponent,
    LoginPopupComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Untitled';  
  @ViewChild('sidenav') sidenav!: MatSidenav;

  isAuthenticated = false;
  isLoginPopupVisible = false;
  loginError = '';

  constructor(private http: HttpClient, private lightbox: Lightbox, private cdRef: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.isAuthenticated = sessionStorage.getItem('isAuthenticated') === 'true';
  }

  toggleSettingsPanel(): void {
    if (this.isAuthenticated) {
      this.sidenav.toggle();
    } else {
      this.isLoginPopupVisible = true;
    }
  }

  hideLoginPopup(): void {
    this.isLoginPopupVisible = false;
  }

  onLoginSuccess(credentials: { username: string; password: string }): void {
    // Here you could use the credentials if needed.
    this.isAuthenticated = true;
    sessionStorage.setItem('isAuthenticated', 'true');
    this.sidenav.open();
  }

  logout(): void {
    this.isAuthenticated = false;
    sessionStorage.removeItem('isAuthenticated');
    this.sidenav.close();
  }
}