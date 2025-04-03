import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedService, MeasurementRecord } from '../../shared.service';
import { HttpClient } from '@angular/common/http';
import { ErrorNotificationService } from '../../services/error-notification.service';
import { timeout, catchError  } from 'rxjs/operators';
import { interval, Subscription, of } from 'rxjs';

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

  // Declare BASE_URL for API calls.
  BASE_URL: string = 'http://localhost:5000/api';

  constructor(private sharedService: SharedService, private http: HttpClient, private errorNotificationService: ErrorNotificationService) {}

  // Compute the measurement record from the inputs.
  get measurementRecord(): MeasurementRecord {
    const now = new Date();
    const pad2 = (n: number) => n.toString().padStart(2, '0');
    const date = `${now.getFullYear()}.${pad2(now.getMonth() + 1)}.${pad2(now.getDate())}`;
    const time = `${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
    const cloggedCount = Number(this.results[0]) || 0;
    // If the clogged count is within the limit, we mark it as "✔", otherwise "❌"
    const resultString = (cloggedCount <= this.ngLimit) ? "✔" : "❌";
    return {
      date,
      time,
      id: this.nozzleId || "-",
      barcode: this.nozzleBarcode || "-",
      operator: this.operatorId || "-",
      clogged: this.results[0] ?? 0,
      partiallyClogged: this.results[1] ?? 0,
      clean: this.results[2] ?? 0,
      result: resultString
    };
  }

  dismiss(): void {
    // 1. Construct the measurement record.
    const record = this.measurementRecord;
  
    this.sharedService.addMeasurementResult(record);


    // 2. Check the DB connection before saving.
    this.http.get<{ message?: string, error?: string }>(
      `${this.BASE_URL}/check-db-connection?ts=${new Date().getTime()}`
    ).pipe(
      timeout(3000),
      catchError(err => {
        console.error("DB connection check failed:", err);
        // Normalize the error response.
        return of({ message: "", error: err.error?.error });
      })
    ).subscribe({
      next: (checkResp) => {
        if (checkResp.message && checkResp.message.trim() !== "") {
          // Connection is OK.
          this.http.post(`${this.BASE_URL}/save-measurement-result`, record).subscribe({
            next: (resp: any) => {
              console.log("Saved to DB:", resp);
            },
            error: (err: any) => {
              console.error("DB save failed:", err);
              this.errorNotificationService.addError({
                code: "E1401",
                message: this.errorNotificationService.getMessage("E1401")
              });
            }
          });
        } else if (checkResp.error) {
          console.error("Database connection not available; measurement not saved.");
          this.errorNotificationService.addError({
            code: "E1401",
            message: this.errorNotificationService.getMessage("E1401")
          });
        }
        // 3. Close the popup regardless of connection check outcome.
        this.closePopup.emit();
      },
      error: err => {
        console.error("Error during DB connection check:", err);
        this.errorNotificationService.addError({
          code: "E1401",
          message: this.errorNotificationService.getMessage("E1401")
        });
        // Ensure popup is dismissed.
        this.closePopup.emit();
      }
    });
  }
}
