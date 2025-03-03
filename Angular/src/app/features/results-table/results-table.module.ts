import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResultsTableComponent } from './results-table.component';

@NgModule({
  imports: [
    CommonModule,
    ResultsTableComponent // ✅ Import the standalone component
  ],
  exports: [ResultsTableComponent] // ✅ Make it available to other modules
})
export class ResultsTableModule {}
