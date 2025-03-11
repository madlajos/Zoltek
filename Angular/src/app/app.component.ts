import { Component, ViewChild, ElementRef, ChangeDetectorRef, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Lightbox } from 'ngx-lightbox';
import { MatSidenav } from '@angular/material/sidenav'; // ✅ Import MatSidenav
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { FormsModule } from '@angular/forms'; // ✅ Import FormsModule


// ✅ Import all standalone components explicitly
import { ImageViewerComponent } from './features/image-viewer/image-viewer.component';
import { ControlPanelComponent } from './features/control-panel/control-panel.component';
import { TurntableControlComponent } from './features/turntable-control/turntable-control.component';
import { ComportControlComponent } from './features/comport-control/comport-control.component';
import { CameraControlComponent } from './features/camera-control/camera-control.component';
import { ResultsTableComponent } from './features/results-table/results-table.component';
import { ErrorPopupListComponent } from './components/error-popup-list/error-popup-list.component';
import { BarcodeScannerControlComponent } from './features/barcode-scanner-control/barcode-scanner-control.component';



@Component({
  selector: 'app-root',
  standalone: true, // ✅ Mark as standalone
  imports: [
    CommonModule, 
    MatSidenavModule, 
    MatButtonModule, 
    MatIconModule, 
    MatExpansionModule,
    FormsModule,

    // ✅ Add standalone components to imports
    ImageViewerComponent,
    ControlPanelComponent,
    TurntableControlComponent,
    ComportControlComponent,
    CameraControlComponent,
    ResultsTableComponent,
    ErrorPopupListComponent,
    BarcodeScannerControlComponent,  
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Untitled';  
  @ViewChild('sidenav') sidenav!: MatSidenav;  // ✅ Reference to sidenav

  isAuthenticated = false; // ✅ Track if the user is logged in
  isLoginPopupVisible = false; // ✅ Controls the login popup
  username = '';
  password = '';
  loginError = '';

  private readonly correctUsername = 'admin';
  private readonly correctPassword = '1234';

  constructor(private http: HttpClient, private lightbox: Lightbox, private cdRef: ChangeDetectorRef) {}

  ngOnInit(): void {
    // Check if the user was previously authenticated (session storage)
    this.isAuthenticated = sessionStorage.getItem('isAuthenticated') === 'true';
  }

  /** ✅ This function runs when clicking the toggle button */
  toggleSettingsPanel(): void {
    if (this.isAuthenticated) {
      this.sidenav.toggle(); // ✅ Open if already authenticated
    } else {
      this.isLoginPopupVisible = true; // ✅ Show login form if not logged in
    }
  }

  /** ✅ Handles login */
  login(): void {
    if (this.username === this.correctUsername && this.password === this.correctPassword) {
      this.isAuthenticated = true;
      sessionStorage.setItem('isAuthenticated', 'true'); // ✅ Store in session
      this.isLoginPopupVisible = false;
      this.sidenav.open(); // ✅ Open settings panel after login
      this.loginError = '';
    } else {
      this.loginError = 'Hibás felhasználónév vagy jelszó!';
    }
  }

  /** ✅ Logout function */
  logout(): void {
    this.isAuthenticated = false;
    sessionStorage.removeItem('isAuthenticated');
    this.sidenav.close();
    this.username = '';
    this.password = '';
  }
}
