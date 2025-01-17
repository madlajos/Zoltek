import { Component, ViewChild, ElementRef, HostListener, ChangeDetectorRef,AfterViewInit,OnInit} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Lightbox } from 'ngx-lightbox';
import { Observable } from 'rxjs';
import { Socket } from 'ngx-socket-io'; // Import Socket from ngx-socket-io
import { MessageService } from './message.service'; // Import the service


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],


})
export class AppComponent implements OnInit {
    title = 'Untitled';  
    @ViewChild('videoPlayer') videoPlayer!: any;
    videoUrl: string | null = null;
    imageUrl: string = 'assets/images/sima.png';
    selectedImage: string | null = null;
    embeddedURL: string | null = null;
    imageList: string[] = [];
    displayedImages: string[] = [];
    imageFilenames: string[] = [];
    inputNumber: string = '';
    selectedFolder: string[]=[];
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

  constructor(private http: HttpClient, private lightbox: Lightbox, private cdRef: ChangeDetectorRef, private messageService: MessageService ) { }


  ngOnInit(): void {

  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }
}

