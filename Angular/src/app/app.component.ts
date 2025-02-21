import { Component, ViewChild, ElementRef, ChangeDetectorRef, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Lightbox } from 'ngx-lightbox';
import { Observable } from 'rxjs';
import { MessageService } from './message.service';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';

// ✅ Import all standalone components explicitly
import { ImageViewerComponent } from './features/image-viewer/image-viewer.component';
import { ControlPanelComponent } from './features/control-panel/control-panel.component';
import { TurntableControlComponent } from './features/turntable-control/turntable-control.component';
import { ComportControlComponent } from './features/comport-control/comport-control.component';
import { CameraControlComponent } from './features/camera-control/camera-control.component';

@Component({
  selector: 'app-root',
  standalone: true, // ✅ Mark as standalone
  imports: [
    CommonModule, 
    MatSidenavModule, 
    MatButtonModule, 
    MatIconModule, 
    MatExpansionModule,

    // ✅ Add standalone components to imports
    ImageViewerComponent,
    ControlPanelComponent,
    TurntableControlComponent,
    ComportControlComponent,
    CameraControlComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Untitled';  
  @ViewChild('videoPlayer') videoPlayer!: any;
  videoUrl: string | null = null;
  selectedImage: string | null = null;
  embeddedURL: string | null = null;
  imageList: string[] = [];
  displayedImages: string[] = [];
  imageFilenames: string[] = [];
  inputNumber: string = '';
  selectedFolder: string[] = [];
  lastThreeImages: any;
  out_files0: string[] = [];
  out_files: string[] = [];
  lampConnected: boolean = false;
  psuConnected: boolean = false;
  printerConnected: boolean = false;
  logMessages: string[] = [];
  showProgressBar = false;
  showModal: string | null = null;
  isSidebarOpen = true;
  @ViewChild('video-container', { static: true }) videoContainer!: ElementRef<HTMLDivElement>;

  constructor(
    private http: HttpClient, 
    private lightbox: Lightbox, 
    private cdRef: ChangeDetectorRef, 
    private messageService: MessageService
  ) {}

  ngOnInit(): void {}

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }
}
