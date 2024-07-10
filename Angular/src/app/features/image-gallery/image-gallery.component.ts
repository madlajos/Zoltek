import { Component, Input } from '@angular/core';
import { SharedService } from '../../shared.service';

@Component({
  selector: 'app-image-gallery',
  templateUrl: './image-gallery.component.html',
  styleUrls: ['./image-gallery.component.css']
})
export class ImageGalleryComponent {
  @Input() images: string[] = [];

  constructor(private sharedService: SharedService) {}

  onImageClick(image: string): void {
    this.sharedService.setSelectedImage(image);
  }
}
