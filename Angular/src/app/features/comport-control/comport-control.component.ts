
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-comport-control',
  templateUrl: './comport-control.component.html',
  styleUrls: ['./comport-control.component.css']
})
export class ComportControlComponent {
    constructor(private http: HttpClient) {}


}