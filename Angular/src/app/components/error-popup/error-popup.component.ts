// src/app/components/error-popup/error-popup.component.ts
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-error-popup',
  standalone: true,
  imports: [CommonModule], // Needed for ngIf/ngStyle
  templateUrl: './error-popup.component.html',
  styleUrls: ['./error-popup.component.css']
})
export class ErrorPopupComponent {
  @Input() message!: string;
  @Input() index!: number; // Position index for stacking
  @Output() close = new EventEmitter<number>();

  // Called when the popup should be dismissed (if needed)
  dismiss() {
    this.close.emit(this.index);
  }
}
