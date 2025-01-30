import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css']
})
export class ControlPanelComponent {
  private readonly BASE_URL = 'http://localhost:5000';
  relayState: boolean = false;  // false = OFF, true = ON

  constructor(private http: HttpClient) {}

  // Toggle Relay Function
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

  // Send "20,1" over serial (Rotate Up)
    // Send "move_turntable_relative" command to rotate up (+20 degrees)
    rotateUp(): void {
      const payload = { degrees: 20 }; // Move by +20 degrees
  
      this.http.post(`${this.BASE_URL}/move_turntable_relative`, payload).subscribe(
        (response: any) => {
          console.log("Turntable moved up 20 degrees", response);
        },
        (error) => {
          console.error("Error moving turntable up:", error);
        }
      );
    }
  
    // Send "move_turntable_relative" command to rotate down (-20 degrees)
    rotateDown(): void {
      const payload = { degrees: -20 }; // Move by -20 degrees
  
      this.http.post(`${this.BASE_URL}/move_turntable_relative`, payload).subscribe(
        (response: any) => {
          console.log("Turntable moved down 20 degrees", response);
        },
        (error) => {
          console.error("Error moving turntable down:", error);
        }
      );
    }
}
