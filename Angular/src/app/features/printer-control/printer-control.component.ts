import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-printer-control',
  templateUrl: './printer-control.component.html',
  styleUrls: ['./printer-control.component.css']
})
export class PrinterControlComponent implements OnInit, OnDestroy {
  private readonly BASE_URL = 'http://localhost:5000';
  movementAmount: number = 1; // Default movement amount
  motorOffState: boolean = false; // Track the state of the MotorOff button

  xPosition: number | string = '?'; // Bind to the X coordinate input
  yPosition: number | string = '?'; // Bind to the Y coordinate input
  zPosition: number | string = '?'; // Bind to the Z coordinate input

  xMin: number = 0; // Minimum X boundary
  xMax: number = 200; // Maximum X boundary
  yMin: number = 0; // Minimum Y boundary
  yMax: number = 200; // Maximum Y boundary

  positionPolling: Subscription | undefined; // Subscription for polling printer position
  connectionPolling: Subscription | undefined; // Subscription for polling printer connection status
  isConnected: boolean = false; // Track the connection status of the printer

  isEditingX: boolean = false; // Flag to track if the X input is being edited
  isEditingY: boolean = false; // Flag to track if the Y input is being edited
  isEditingZ: boolean = false; // Flag to track if the Z input is being edited

  xHomed: boolean = false;
  yHomed: boolean = false;
  zHomed: boolean = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadSettings();
    this.startConnectionPolling();
  }

  ngOnDestroy(): void {
    this.stopPollingPosition();
    this.stopConnectionPolling();
  }
  
  loadSettings(): void {
    this.http.get('assets/settings.json').subscribe(
      (settings: any) => {
        this.xMin = settings.boundaries.x.min;
        this.xMax = settings.boundaries.x.max;
        this.yMin = settings.boundaries.y.min;
        this.yMax = settings.boundaries.y.max;
      },
      (error) => {
        console.error('Failed to load settings', error);
      }
    );
  }

  startPollingPosition(): void {
    this.positionPolling = interval(1000).subscribe(() => {
      this.updatePrinterPosition();
    });
  }

  stopPollingPosition(): void {
    this.positionPolling?.unsubscribe();
  }

  startConnectionPolling(): void {
    this.connectionPolling = interval(5000).subscribe(() => {
      this.checkPrinterConnection();
    });
  }

  stopConnectionPolling(): void {
    this.connectionPolling?.unsubscribe();
  }

  checkPrinterConnection(): void {
    this.http.get<{ connected: boolean }>(`${this.BASE_URL}/api/status/printer`).subscribe(
      (response) => {
        const wasConnected = this.isConnected;
        this.isConnected = response.connected;
        if (this.isConnected && !wasConnected) {
          this.startPollingPosition();
        } else if (!this.isConnected && wasConnected) {
          this.stopPollingPosition();
        }
      },
      (error) => {
        console.error('Failed to check printer connection status!', error);
        this.isConnected = false;
        this.stopPollingPosition();
      }
    );
  }

  updatePrinterPosition(): void {
    if (this.isConnected && !this.motorOffState) {
      this.http.get<{ x: number, y: number, z: number }>(`${this.BASE_URL}/get_printer_position`).subscribe(
        (position) => {
          if (!this.isEditingX && this.xHomed) {
            this.xPosition = position.x;
          }
          if (!this.isEditingY && this.yHomed) {
            this.yPosition = position.y;
          }
          if (!this.isEditingZ && this.zHomed) {
            this.zPosition = position.z;
          }
        },
        (error) => {
          console.error('Failed to get printer position!', error);
        }
      );
    }
  }

  movePrinterRelative(axis: string, value: number) {
    if (this.motorOffState) {
        console.error('Cannot move printer while motors are off.');
        return;
    }
    this.resetMotorOffState();

    if ((axis === 'x' && !this.xHomed) || (axis === 'y' && !this.yHomed) || (axis === 'z' && !this.zHomed)) {
      console.error(`Cannot move ${axis.toUpperCase()} axis because it is not homed.`);
      return;
    }

    let newPosition;
    if (axis === 'x') {
        newPosition = (typeof this.xPosition === 'number' ? this.xPosition : 0) + value;
        if (newPosition < this.xMin || newPosition > this.xMax) {
            console.error(`X position ${newPosition} out of bounds!`);
            return;
        }
    } else if (axis === 'y') {
        newPosition = (typeof this.yPosition === 'number' ? this.yPosition : 0) + value;
        if (newPosition < this.yMin || newPosition > this.yMax) {
            console.error(`Y position ${newPosition} out of bounds!`);
            return;
        }
    }

    const payload = { axis, value };
    this.http.post(`${this.BASE_URL}/move_printer_relative`, payload).subscribe(
        (response: any) => {
            console.log('Printer moved successfully!', response);
        },
        (error: any) => {
            console.error('Failed to move printer!', error);
        }
    );
  }

  homeAxis(axis?: string): void {
    this.resetMotorOffState();

    const payload = { axes: axis ? [axis] : [] };
    this.http.post(`${this.BASE_URL}/home_printer`, payload).subscribe(
        (response) => {
            console.log(`Printer ${axis ? axis.toUpperCase() : 'all'} axis homed successfully!`, response);
            if (axis) {
                if (axis === 'x') {
                    this.xPosition = 0;
                    this.xHomed = true;
                } else if (axis === 'y') {
                    this.yPosition = 0;
                    this.yHomed = true;
                } else if (axis === 'z') {
                    this.zPosition = 0;
                    this.zHomed = true;
                }
            } else {
                // If homing all axes, reset all positions
                this.xPosition = 0;
                this.yPosition = 0;
                this.zPosition = 0;
                this.xHomed = true;
                this.yHomed = true;
                this.zHomed = true;
            }
        },
        (error) => {
            console.error(`Failed to home printer ${axis ? axis.toUpperCase() : 'all'} axis!`, error);
        }
    );
  }

  setMovementAmount(amount: number): void {
    this.movementAmount = amount;
    console.log('Movement amount set to', this.movementAmount);
  }

  motorOff(): void {
    const payload = { axes: [] };
    this.http.post(`${this.BASE_URL}/disable_stepper`, payload).subscribe(
      (response) => {
        console.log('Printer motors disabled successfully!', response);
        this.motorOffState = true;
        this.xPosition = "?";
        this.yPosition = "?";
        this.zPosition = "?";
        this.xHomed = false;
        this.yHomed = false;
        this.zHomed = false;
      },
      (error) => {
        console.error('Failed to disable printer motors!', error);
      }
    );
  }

  movePrinterAbsolute(x?: number | string, y?: number | string, z?: number | string): void {
    if (this.motorOffState) {
        console.error('Cannot move printer while motors are off.');
        return;
    }
    this.resetMotorOffState();

    if ((x === undefined || x === "?") && !this.xHomed) {
        console.error('Cannot move X axis because it is not homed.');
        return;
    }

    if ((y === undefined || y === "?") && !this.yHomed) {
        console.error('Cannot move Y axis because it is not homed.');
        return;
    }

    if ((z === undefined || z === "?") && !this.zHomed) {
        console.error('Cannot move Z axis because it is not homed.');
        return;
    }

    // Convert to numbers if necessary
    x = typeof x === 'number' ? x : (x !== undefined ? Number(x) : undefined);
    y = typeof y === 'number' ? y : (y !== undefined ? Number(y) : undefined);
    z = typeof z === 'number' ? z : (z !== undefined ? Number(z) : undefined);

    if ((x !== undefined && (x < this.xMin || x > this.xMax)) || (y !== undefined && (y < this.yMin || y > this.yMax))) {
        console.error('New position out of bounds!');
        return;
    }

    const payload = { x, y, z };
    this.http.post(`${this.BASE_URL}/move_printer_absolute`, payload).subscribe(
        (response) => {
            console.log('Printer moved to the specified position successfully!', response);
        },
        (error) => {
            console.error('Failed to move printer to the specified position!', error);
        }
    );
  }

  resetMotorOffState(): void {
    this.motorOffState = false;
    this.updatePrinterPosition(); // Immediately update position after motors are enabled
  }

  onFocus(input: string): void {
    if (input === 'x') {
      this.isEditingX = true;
    } else if (input === 'y') {
      this.isEditingY = true;
    } else if (input === 'z') {
      this.isEditingZ = true;
    }
  }

  onBlur(input: string): void {
    if (input === 'x') {
      this.isEditingX = false;
    } else if (input === 'y') {
      this.isEditingY = false;
    } else if (input === 'z') {
      this.isEditingZ = false;
    }
  }
}
