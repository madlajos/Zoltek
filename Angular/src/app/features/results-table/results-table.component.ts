import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedService } from '../../shared.service';

interface MeasurementResult {
  date: string;
  time: string;
  id: number | string;
  barcode: string;
  operator: string;
  clogged: number | string;
  partiallyClogged: number | string;
  clean: number | string;
  result: string;
}

@Component({
  standalone: true,
  selector: 'app-results-table',
  imports: [CommonModule],
  templateUrl: './results-table.component.html',
  styleUrls: ['./results-table.component.css']
})
export class ResultsTableComponent implements OnInit {
  results: MeasurementResult[] = [];

  constructor(private sharedService: SharedService) {}

  ngOnInit(): void {
    // Pre-fill table with 5 empty rows before measurements arrive
    this.results = Array.from({ length: 12 }, (_, i) => ({
      date: '2025.03.21',
      time: '12:32',
      id: '1234',
      barcode: '5678',
      operator: 'Teszt Béla',
      clogged: '12',
      partiallyClogged: '821',
      clean: '48012',
      result: 'OK'
    }));
  }
}
