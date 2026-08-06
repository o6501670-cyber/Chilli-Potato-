import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-location-selector',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './location-selector.html',
  styleUrl: './location-selector.css'
})
export class LocationSelectorComponent {
  @Input() centers: any[] = [];
  @Input() hasGlobalAccess: boolean = false;
  @Input() selectedCenterId: number | null = null;
  @Output() selectedCenterIdChange = new EventEmitter<number | null>();
  @Output() selectionChange = new EventEmitter<void>();

  isOpen = false;

  get selectedCenterName() {
    if (this.selectedCenterId === null) return 'All Locations';
    const center = this.centers.find(c => c.id === this.selectedCenterId);
    return center ? (center.display_name || center.center_name || center.name) : 'Select Location';
  }

  selectCenter(id: number | null) {
    this.selectedCenterId = id;
    this.selectedCenterIdChange.emit(id);
    this.selectionChange.emit();
    this.isOpen = false;
  }
}
