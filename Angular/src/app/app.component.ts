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
    @ViewChild('video-container', { static: true }) videoContainer!: ElementRef<HTMLDivElement>;

  constructor(private http: HttpClient, private lightbox: Lightbox, private cdRef: ChangeDetectorRef, private messageService: MessageService ) { }

 

  ngOnInit(): void {
    this.connectToLamp();
    setTimeout(() => {
      this.startVideo_cont();
    }, 100); // Add a delay of 10 seconds (10000 milliseconds)
  }
  
  connectToLamp(): void {
    this.http.post('http://localhost:5000//connect-to-lamp', {}).subscribe(
      (response) => {
        console.log('Lamp connected successfully!', response);
        this.lampConnected = true; // Set lampConnected to true when the connection succeeds
        // Proceed to connect to the printer after a delay
        setTimeout(() => {
          this.connectToPrinter();
        }, 1000); // Add a delay of 10 seconds (10000 milliseconds)
      },
      (error) => {
        console.error('Failed to connect to lamp!', error);
      }
    );
  }

 
  connectToPrinter(): void {
    this.http.post('http://localhost:5000//connect-to-printer', {}).subscribe(
      (response) => {
        console.log('Printer homed successfully!', response);
        this.printerConnected = true; // Set lampConnected to true when the connection succeeds
        // Proceed to connect to the printer after a delay
        setTimeout(() => {
          this.connectToPSU();
        }, 1000); // Add a delay of 10 seconds (10000 milliseconds)
        // You can handle the response here if needed
      },
      (error) => {
        console.error('Failed to home printer!', error);
      }
    );
  }


  connectToPSU(): void {
    this.http.post('http://localhost:5000//connect-to-psu', {}).subscribe(
      (response) => {
        console.log('Printer homed successfully!', response);
        this.psuConnected = true; // Set lampConnected to true when the connection succeeds
        // Proceed to connect to the printer after a delay
        setTimeout(() => {
          
        }, 1000); // Add a delay of 10 seconds (10000 milliseconds)
        // You can handle the response here if needed
      },
      (error) => {
        console.error('Failed to home printer!', error);
      }
    );
  }


  showImage(imageDataUrl: string): void {
    this.showModal = 'data:image/jpg;base64,'+ imageDataUrl;
    console.log('Printer homed successfully!', this.showModal);
  }

  closeImageModal(): void {
    this.showModal = null;
  }




  printerHome(): void {
    this.http.post('http://localhost:5000//printer_home', {}).subscribe(
      (response) => {
        console.log('Printer homed successfully!', response);
        // You can handle the response here if needed
      },
      (error) => {
        console.error('Failed to home printer!', error);
      }
    );
  }



  captureAndSendExpo(): void {
    this.http.post('http://127.0.0.1:5000/capture-and-send-expo', { number: this.inputNumber }).subscribe(
      (response: any) => {
        console.log(response);
      },
      (error) => {
        console.error(error);
      }
    );
  }

  Lampwrite(): void {
    this.http.post<any>('http://localhost:5000/connect-to-lamp2', {}).subscribe(
      (response) => {
        console.log(response);
        // Add a delay of 5 seconds (5000 milliseconds) before calling connectToPrinter
        
        },
      (error) => {
        console.error(error);
        // Handle error response
      }
    );
  }

 
  fetchImages(): void {
    this.http.get('http://localhost:5000/get-images', { responseType: 'blob' })
      .subscribe(
        (data: Blob) => {
          const reader = new FileReader();
          reader.onload = () => {
            // Convert binary image data to data URL
            const imageDataUrl = reader.result as string;
            this.imageList.push(imageDataUrl);
          };
          reader.readAsDataURL(data);
        },
        error => {
          console.error('Error:', error);
        }
      );
  }



  onClickSendVISToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lamp', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }

  onClickSendUV1ToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lampUV1', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }

  

  onClickSendUV2ToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lampUV2', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }

  onClickSendUV3ToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lampUV3', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }

  onClickSendUV4ToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lampUV4', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }
  onClickSendUV5ToBackend(channel: number) {
    this.http.post('http://localhost:5000/turn-on-lampUV5', { channel: 1 })
      .subscribe(response => {
        console.log('Response from backend:', response);
      });
  }
  
  openURL(videoUrl: string): void {
    const container: HTMLDivElement | null = this.videoContainer?.nativeElement;
    if (container) {
      container.innerHTML = `<iframe src="${videoUrl}" frameborder="0" style="width: 819px; height: 600px;"></iframe>`;
    }}


   
    printerMove1(): void {
      this.http.post('http://localhost:5000//printer_move1', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove2(): void {
      this.http.post('http://localhost:5000//printer_move2', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }
 
    printerMove3(): void {
      this.http.post('http://localhost:5000//printer_move3', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove4(): void {
      this.http.post('http://localhost:5000//printer_move4', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }
    printerMove5(): void {
      this.http.post('http://localhost:5000//printer_move5', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove6(): void {
      this.http.post('http://localhost:5000//printer_move6', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove7(): void {
      this.http.post('http://localhost:5000//printer_move7', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove8(): void {
      this.http.post('http://localhost:5000//printer_move8', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }
    printerMove9(): void {
      this.http.post('http://localhost:5000//printer_move9', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove10(): void {
      this.http.post('http://localhost:5000//printer_move10', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }
    printerMove11(): void {
      this.http.post('http://localhost:5000//printer_move11', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove12(): void {
      this.http.post('http://localhost:5000//printer_move12', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove13(): void {
      this.http.post('http://localhost:5000//printer_move13', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }
    printerMove14(): void {
      this.http.post('http://localhost:5000//printer_move14', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }


    printerMove15(): void {
      this.http.post('http://localhost:5000//printer_move15', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }


    printerMove16(): void {
      this.http.post('http://localhost:5000//printer_move16', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }

    printerMove17(): void {
      this.http.post('http://localhost:5000//printer_move17', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
    }


    printerMove18(): void {
      this.http.post('http://localhost:5000//printer_move18', {}).subscribe(
        (response) => {
          console.log('Printer homed successfully!', response);
          // You can handle the response here if needed
        },
        (error) => {
          console.error('Failed to home printer!', error);
        }
      );
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

  loadLastThreeImages(): void {
    this.http.post<string>('http://127.0.0.1:5000/get-last-three-images', {}).subscribe(
      (imagePath: string) => { // Explicitly specify the type of imagePath as string
        if (typeof imagePath === 'string') {
          // Treat the single image path as an array with a single element
          const imagePathString: string = imagePath; // Type assertion
          this.lastThreeImages = [imagePathString.replace(/\\/g, '/')];
          console.log('Last three images:', this.lastThreeImages);
          this.lastThreeImages.forEach((imagePath: string) => { // Explicitly specify the type of imagePath in forEach loop
            this.loadImageFromFile(imagePath);
          });
        } else {
          console.error('Unexpected response from server:', imagePath);
          this.lastThreeImages = [];
        }
      },
      error => {
        console.error('Error fetching images:', error);
      }
    );
  }
  
  
  loadImageFromFile(imagePath: string | undefined): void {
    if (imagePath) {
      this.displayedImages.push(imagePath);
    } else {
      console.error('Invalid imagePath:', imagePath);
    }
  }

  onSelectFolder(): void {
    this.http.get<any>('http://localhost:5000/select-folder').subscribe(
      (response) => {
        console.log('Selected folder:', response.folder);
        this.selectedFolder = response.folder; // Update selected folder
      },
      (error) => {
        console.error('Error selecting folder:', error);
        // Handle error
      }
    );
  }

  startVideo(): void {
  const videoUrl = 'http://localhost:5000/video-stream';
  const videoContainer = document.querySelector('.video-container') as HTMLElement;

  // Set the background image of the container to the video stream URL
  videoContainer.style.position ="absolute" ;
  videoContainer.style.backgroundImage = `url(${videoUrl})`;
  videoContainer.style.backgroundSize = 'cover'; // You can adjust the sizing as needed
  videoContainer.style.width = '600px'; // Set the desired width
  videoContainer.style.height = '600px'; // Set the desired height
  videoContainer.style.border = '0px solid rgb(250,250,250)'; // Optional: Add a border for styling
  videoContainer.style.backgroundRepeat = 'no-repeat';
  videoContainer.style.marginLeft ="-30%" ;
  videoContainer.style.marginTop ="5%" ;
  videoContainer.style.zIndex ="0" ;
  // Remove any existing content within the container
  videoContainer.innerHTML = '';
}




startVideo_cont(): void {
  const videoContainer = document.querySelector('.video-container') as HTMLElement;
  // Set the background image of the container to the video stream URL
  videoContainer.style.position ="absolute" ;

  videoContainer.style.backgroundSize = 'cover'; // You can adjust the sizing as needed
  videoContainer.style.width = '600px'; // Set the desired width
  videoContainer.style.height = '600px'; // Set the desired height
  videoContainer.style.backgroundRepeat = 'no-repeat';
  videoContainer.style.marginLeft ="-30%" ;
  videoContainer.style.marginTop ="5%" ;
  videoContainer.style.zIndex ="0" ;
  videoContainer.style.boxShadow = "0 4px 17px rgba(42, 98, 140, 0.35)";
  ;

}


  startVideoStream(): void {
    const videoUrl = 'http://localhost:5000/video-stream';
    const video = document.querySelector('.video-container video') as HTMLVideoElement;
    
    if (video) {
      video.src = videoUrl;
      video.autoplay = true;
      this.cdRef.detectChanges();
    }
  }


  changeImage1() {
    // Change the image URL to a new image
    this.imageUrl = 'assets/images/VIS.png'; // Change 'new_image.jpg' to your new image file
  }

  changeImage2() {
    // Change the image URL to a new image
    this.imageUrl = 'assets/images/UV_1.png'; // Change 'new_image.jpg' to your new image file
  }

  changeImage3() {
    // Change the image URL to a new image
    this.imageUrl = 'assets/images/UV_2.png'; // Change 'new_image.jpg' to your new image file
  }
  
  changeImage4() {
    // Change the image URL to a new image
    this.imageUrl = 'assets/images/UV_1.png'; // Change 'new_image.jpg' to your new image file
  }
   

  
  sendFloat(): void {
    const floatValue = 3.14; // Replace with your float value

    this.http.post<string[]>('http://localhost:5000/backend-url', { floatValue }).subscribe(
      (response) => {
        console.log(response);
          console.log(response);
          this.out_files0 = response;
          // Handle response from the backend
        },
        error => {
          // Handle error
          console.error(error);
        }
      );
  }

}

