import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedService, MeasurementRecord } from '../../shared.service';

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
  @Input() nozzleId!: string;
  @Input() nozzleBarcode!: string;
  @Input() operatorId!: string;
  @Input() ngLimit!: number;
  @Output() closePopup = new EventEmitter<void>();

  constructor(private sharedService: SharedService) {}  // inject SharedService


  dismiss(): void {
    // When OK is clicked, assemble the measurement record
    const now = new Date();
    const pad2 = (n: number) => n.toString().padStart(2, '0');
    const date = `${now.getFullYear()}.${pad2(now.getMonth()+1)}.${pad2(now.getDate())}`;
    const time = `${pad2(now.getHours())}:${pad2(now.getMinutes())}`;

    const cloggedCount = Number(this.results[0]) || 0;
    const resultString = (cloggedCount <= this.ngLimit) ? "OK" : "NO";

    const record: MeasurementRecord = {
      date,
      time,
      id: this.nozzleId || "",
      barcode: this.nozzleBarcode || "",
      operator: this.operatorId || "",
      clogged: this.results[0] ?? 0,
      partiallyClogged: this.results[1] ?? 0,
      clean: this.results[2] ?? 0,
      result: resultString
    };
    this.sharedService.addMeasurementResult(record);

    // Emit event to close the popup
    this.closePopup.emit();
  }
}
