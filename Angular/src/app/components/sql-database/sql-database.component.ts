import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-sql-database',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sql-database.component.html',
  styleUrls: ['./sql-database.component.css']
})
export class SQLDatabaseComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000/api';

  // Local model for SQL Server settings.
  server: string = "";
  db_name: string = "";
  username: string = "";
  password: string = "";

  // Connection state.
  connected: boolean = false;
  connectionStatus: string = "Not Connected";

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    // Load SQL settings from backend.
    this.http.get<{ sql_server: any }>(`${this.BASE_URL}/get-other-settings?category=sql_server`)
      .subscribe({
        next: response => {
          if (response && response.sql_server) {
            this.server = response.sql_server.server;
            this.db_name = response.sql_server.db_name;
            this.username = response.sql_server.username;
            this.password = response.sql_server.password;
          }
        },
        error: err => {
          console.error("Failed to load SQL Server settings:", err);
        }
      });
  }

  // Update a specific setting.
  updateSetting(settingName: string, value: any): void {
    this.http.post(`${this.BASE_URL}/update-other-settings`, {
      category: "sql_server",
      setting_name: settingName,
      setting_value: value
    }).subscribe({
      next: (response: any) => {
        console.log(`Updated ${settingName}:`, response);
      },
      error: err => {
        console.error(`Failed to update ${settingName}:`, err);
      }
    });
  }

  // Called when the user changes a textbox.
  onSettingChange(settingName: string, event: any): void {
    const newValue = event.target.value;
    this.updateSetting(settingName, newValue);
  }

  // Connect to the SQL database.
  connectDatabase(): void {
    this.http.get<{ message?: string, error?: string }>(`${this.BASE_URL}/connect_sql_database`)
      .subscribe({
        next: response => {
          if (response.message) {
            this.connectionStatus = response.message;
            this.connected = true;
          }
        },
        error: err => {
          console.error("Failed to connect to SQL database:", err);
          this.connectionStatus = err.error?.error || "Connection failed";
          this.connected = false;
        }
      });
  }

  // Disconnect from the SQL database.
  disconnectDatabase(): void {
    this.http.post(`${this.BASE_URL}/disconnect_sql_database`, {}).subscribe({
      next: response => {
        console.log("Disconnected from SQL database:", response);
        this.connected = false;
        this.connectionStatus = "Disconnected";
      },
      error: err => {
        console.error("Failed to disconnect SQL database:", err);
      }
    });
  }

  // Toggle connection.
  toggleConnection(): void {
    if (this.connected) {
      this.disconnectDatabase();
    } else {
      this.connectDatabase();
    }
  }
}
