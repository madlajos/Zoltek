import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-measurement-results-popup',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './measurement-results-popup.component.html',
  styleUrls: ['./measurement-results-popup.component.css']
})
export class MeasurementResultsPopupComponent {
  // Expect an array of three numbers for the results.
  @Input() results: number[] = [];
  @Output() closePopup = new EventEmitter<void>();

  dismiss(): void {
    this.closePopup.emit();
  }
}
