import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { catchError, concatMap, delay, tap } from 'rxjs/operators';

interface Device {
  name: string;
  status: string;
  action: string;
}

@Component({
  selector: 'app-comport-control',
  templateUrl: './comport-control.component.html',
  styleUrls: ['./comport-control.component.css']
})
export class ComportControlComponent implements OnInit {
  devices: Device[] = [
    { name: 'Printer', status: 'Disconnected', action: 'Connect' },
    { name: 'Lampcontroller', status: 'Disconnected', action: 'Connect' },
    { name: 'PSU', status: 'Disconnected', action: 'Connect' }
  ];

  private readonly BASE_URL = 'http://localhost:5000/api';

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    this.checkStatusAndConnectDevices();
  }

  checkStatusAndConnectDevices(): void {
    this.devices.reduce((previous, device) => {
      return previous.pipe(
        delay(1000),
        concatMap(() => this.http.get<{ connected: boolean; port: string }>(`${this.BASE_URL}/status/${device.name.toLowerCase()}`).pipe(
          tap((status: any) => {
            if (status.connected) {
              device.status = `Connected (${status.port})`;
              device.action = 'Disconnect';
            } else {
              device.status = 'Disconnected';
              device.action = 'Connect';
              this.toggleConnection(device);
            }
          }),
          catchError(error => {
            console.error(`Error fetching status for ${device.name}:`, error);
            device.status = 'Error';
            device.action = 'Connect';
            return of(null);
          })
        ))
      );
    }, of(null)).subscribe();
  }

  toggleConnection(device: Device): void {
    const action = device.action.toLowerCase();
    console.log(`${action.charAt(0).toUpperCase() + action.slice(1)}ing ${device.name}...`);
    this.http.post(`${this.BASE_URL}/${action}-to-${device.name.toLowerCase()}`, {})
      .pipe(
        tap(() => {
          console.log(`${device.name} ${action}ed successfully.`);
          this.checkStatus();  // Update status after the connection action completes
        }),
        catchError(error => {
          console.error(`Error ${action}ing ${device.name}:`, error);
          device.status = 'Error';
          return of(null); // Return a null observable to handle the error
        })
      ).subscribe();
  }

  checkStatus(): void {
    this.devices.forEach(device => {
      console.log(`Checking status for ${device.name}...`);
      this.http.get(`${this.BASE_URL}/status/${device.name.toLowerCase()}`).pipe(
        tap((status: any) => {
          console.log(`Received status for ${device.name}:`, status);
          device.status = status.connected ? `Connected (${status.port})` : 'Disconnected';
          device.action = status.connected ? 'Disconnect' : 'Connect';
        }),
        catchError(error => {
          console.error(`Error fetching status for ${device.name}:`, error);
          device.status = 'Error';
          device.action = 'Connect';
          return of(null); // Return an observable with a null value in case of error
        })
      ).subscribe();
    });
  }
}
