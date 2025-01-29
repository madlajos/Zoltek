import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css']
})
export class ControlPanelComponent {
  private readonly BASE_URL = 'http://localhost:5000/api';
  relayState: boolean = false;  // false = OFF, true = ON

  constructor(private http: HttpClient) {}

  toggleRelay(): void {
    this.relayState = !this.relayState;  // Toggle relay state
    const payload = { state: this.relayState ? 1 : 0 };

    this.http.post(`${this.BASE_URL}/toggle-relay`, payload).subscribe(
      (response: any) => {
        console.log(`Relay ${this.relayState ? 'ON' : 'OFF'}`, response);
      },
      (error) => {
        console.error('Error toggling relay:', error);
        this.relayState = !this.relayState;  // Revert state if failed
      }
    );
  }
}
