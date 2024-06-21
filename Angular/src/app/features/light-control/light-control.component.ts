
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-light-control',
  templateUrl: './light-control.component.html',
  styleUrls: ['./light-control.component.css']
})
export class LightControlComponent {
    constructor(private http: HttpClient) {}


}