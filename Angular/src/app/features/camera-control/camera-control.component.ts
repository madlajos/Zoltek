import { Component, OnInit, ElementRef, ViewChild, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-camera-control',
  templateUrl: './camera-control.component.html',
  styleUrls: ['./camera-control.component.css']
})
export class CameraControlComponent implements OnInit {
  @ViewChild('videoPlayer') videoPlayer!: any;
  videoUrl: string | null = null;
  imageUrl: string = 'assets/images/sima.png';
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
  @ViewChild('video-container', { static: true }) videoContainer!: ElementRef<HTMLDivElement>;

  constructor(private http: HttpClient, private cdRef: ChangeDetectorRef) { }

  ngOnInit(): void {
    
  }

  openURL(videoUrl: string): void {
    const container: HTMLDivElement | null = this.videoContainer?.nativeElement;
    if (container) {
      container.innerHTML = `<iframe src="${videoUrl}" frameborder="0" style="width: 819px; height: 600px;"></iframe>`;
    }
  }

  captureImage(): void {
    this.http.post('http://127.0.0.1:5000/capture-image', {}).subscribe(
      (response) => {
        console.log(response);
      },
      (error) => {
        console.error(error);
      }
    );
  }

  startVideoStream(): void {
    const videoUrl = 'http://localhost:5000/video-stream';
    const videoContainer = document.querySelector('.video-container') as HTMLElement;

    const img = document.createElement('img');
    img.src = videoUrl;
    img.style.width = '100%';
    img.style.height = '100%';

    videoContainer.innerHTML = '';
    videoContainer.appendChild(img);
  }
}