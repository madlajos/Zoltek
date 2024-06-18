import { Component } from '@angular/core';
import { MessageService } from '../message.service'; // Import the service

@Component({
  selector: 'app-message-display',
  templateUrl: './message-display.component.html',
  styleUrls: ['./message-display.component.css']
})
export class MessageDisplayComponent {
  constructor(private messageService: MessageService) {} // Inject the service

  getMessages(): string[] {
    return this.messageService.getMessages(); // Retrieve messages
  }
}