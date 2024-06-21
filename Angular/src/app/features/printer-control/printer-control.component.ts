// src/app/features/printer-control/printer-control.component.ts
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http'; // Import HttpClient

@Component({
  selector: 'app-printer-control',
  templateUrl: './printer-control.component.html',
  styleUrls: ['./printer-control.component.css']
})
export class PrinterControlComponent {
    constructor(private http: HttpClient) {}

    movePrinter(axis: string, value: number){
        const payload = { axis, value };
        this.http.post('http://localhost:5000//move_printer', {}).subscribe(
          (response: any) => {
            console.log('Printer moved successfully!', response);
            // You can handle the response here if needed
          },
          (error: any) => {
            console.error('Failed to move printer!', error);
          }
        );
    }
}

