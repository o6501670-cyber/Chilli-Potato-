Created At: 2026-07-13T04:58:51Z
Completed At: 2026-07-13T04:58:51Z
File Path: `file:///c:/Users/Dell/OneDrive%20-%20CINNTRA%20INFO%20TECH%20SOLUTIONS%20PRIVATE%20LIMITED/Desktop/chowmein/chowmein/chowmein/properback/properback/frontend/src/app/billing/billing.ts`
Total Lines: 815
Total Bytes: 27460
Showing lines 1 to 800
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
2: import { ActivatedRoute } from '@angular/router';
3: import { CommonModule } from '@angular/common';
4: import { FormsModule } from '@angular/forms';
5: import { ApiService } from '../services/api';
6: 
7: @Component({
8:   selector: 'app-billing',
9:   standalone: true,
10:   imports: [CommonModule, FormsModule],
11:   templateUrl: './billing.html',
12:   styleUrls: ['./billing.css']
13: })
14: export class BillingComponent implements OnInit {
15:   apiService = inject(ApiService);
16:   cdr = inject(ChangeDetectorRef);
17:   route = inject(ActivatedRoute);
18: 
19:   viewMode: 'landing' | 'new-invoice' = 'landing';
20: 
21:   centers: any[] = [];
22:   selectedCenterId: number | null = null;
23: 
24:   // Landing view data
25:   globalInvoices: any[] = [];
26:   appointments: any[] = [];
27:   staffActivity: any[] = [];
28: 
29:   get selectedCenterName(): string {
30:     if (!this.selectedCenterId || !this.centers) return 'All Centers';
31:     const center = this.centers.find(c => c.id === this.selectedCenterId);
32:     return center ? center.display_name : 'All Centers';
33:   }
34: 
35:   // New Invoice view data
36:   searchPhone: string = '';
37:   clients: any[] = [];
38:   client: any = null;
39:   clientInvoices: any[] = [];
40:   clientServiceHistory: any[] = [];
41:   clientAdvances: any[] = [];
42:   clientAdvanceBalance: number = 0;
43:   clientHistory: any[] = [];
44:   useAdvancePayment: boolean = false;
45: 
46:   advances: any[] = [];
47: 
48:   services: any[] = [];
49:   products: any[] = [];
50:   memberships: any[] = [];
51:   packages: any[] = [];
52:   cards: any[] = [];
53:   staffMembers: any[] = [];
54:   
55:   currentInvoiceId: number | null = null;
56:   promotions: any[] = [];
57:   selectedPromotion: any = null;
58:   configStaffIds: number[] = [];
59:   
60:   showCheckoutModal: boolean = false;
61:   checkoutPayments: any[] = [];
62:   checkoutRemaining: number = 0;
63: 
64: 
65:   cart: any[] = [];
66:   activeTab: 'search' | 'cards' | 'packages' | 'memberships' | 'advance' = 'search';
67:   searchServiceTerm = '';
68:   searchProductTerm = '';
69: 
70:   // Detailed Configuration State
71:   selectedItemForConfig: any = null;
72:   configType: 'service' | 'product' | 'card' | 'advance' | 'package' | 'membership' | null = null;
73:   managerDiscountPercent: number = 0;
74:   managerDiscountAmount: number = 0;
75:   finalConfigPrice: number = 0;
76:   configStaffId: any = null;
77:   advanceAmount: number = 0;
78:   advanceDescription: string = '';
79: 
80:   // Taxes and Discounts
81:   invoiceDiscount: number = 0;
82:   invoiceCGST: number = 0;
83:   invoiceSGST: number = 0;
84: 
85:   // Package Config
86:   packageSearchTerm: string = '';
87:   packageSelectedServices: any[] = [];
88: 
89:   isOwner = false;
90:   permissions: any = {};
91: 
92:   ngOnInit(): void {
93:     console.log('BillingComponent initialized');
94:     this.route.queryParams.subscribe(params => {
95:       if (params['appointment_id']) {
96:         this.loadAppointmentIntoBilling(params['appointment_id']);
97:       }
98:     });
99:     const userStr = localStorage.getItem('user');
100:     if (userStr) {
101:       try {
102:         const user = JSON.parse(userStr);
103:         this.permissions = user.permissions || {};
104:         this.isOwner = user.role === 'Owner' || user.is_superuser === true;
105:       } catch (e) {}
106:     }
107:     this.loadCenters();
108:   }
109: 
110:   loadAppointmentIntoBilling(appointmentId: string | number) {
111:     this.apiService.get('appointments/api/appointments/' + appointmentId + '/').subscribe((appt: any) => {
112:       if (!appt) return;
113: 
114:       if (appt.center && this.selectedCenterId !== appt.center) {
115:         this.selectedCenterId = appt.center;
116:         this.loadMasters();
117:       }
118:       
119:       this.apiService.getClients(appt.client_phone).subscribe({
120:         next: (clients: any[]) => {
121:           const existingClient = (clients || []).find(c => c.phone === appt.client_phone);
122:           if (existingClient) {
123:             this.selectClient(existingClient);
124:           } else {
125:             this.client = {
126:               name: appt.client_name,
127:               phone: appt.client_phone,
128:             };
129:             this.searchPhone = appt.client_phone;
130:           }
131:           
132:           this.openNewInvoice();
133:           
134:           if (appt.services && appt.services.length > 0) {
135:             let attempts = 0;
136:             const populateCart = () => {
137:               if (this.services.length === 0 && attempts < 10) {
138:                 attempts++;
139:                 setTimeout(populateCart, 300);
140:                 return;
141:               }
142:               appt.services.forEach((s: any) => {
143:                 const matchedService = this.services.find(ms => ms.name === s.service_name);
144:                 const objId = matchedService ? matchedService.id : null;
145:                 
146:                 this.cart.push({
147:                   content_type: 'services.servicemaster',
148:                   object_id: objId,
149:                   description: s.service_name,
150:                   unit_price: Number(s.price),
151:                   discount: 0,
152:                   quantity: 1,
153:                   staff_members: s.staff ? [Number(s.staff)] : []
154:                 });
155:               });
156:               this.cdr.detectChanges();
157:             };
158:             populateCart();
159:           } else {
160:             this.cdr.detectChanges();
161:           }
162:         },
163:         error: (err: any) => {
164:           this.client = {
165:             name: appt.client_name,
166:             phone: appt.client_phone,
167:           };
168:           this.searchPhone = appt.client_phone;
169:           this.openNewInvoice();
170:           this.cdr.detectChanges();
171:         }
172:       });
173:     }, (err: any) => {
174:       console.error("Failed to load appointment", err);
175:     });
176:   }
177: 
178:   loadCenters() {
179:     this.apiService.getCenters().subscribe((data: any[]) => {
180:       this.centers = data || [];
181:       if (this.centers.length && !this.selectedCenterId) {
182:         this.selectedCenterId = this.centers[0].id;
183:       }
184:       this.loadLandingData();
185:       this.loadMasters();
186:     }, (err: any) => {
187:       console.error('Failed to load centers', err);
188:     });
189:   }
190: 
191:   onCenterChange() {
192:     this.loadLandingData();
193:     this.loadMasters();
194:   }
195: 
196:   loadLandingData() {
197:     // 1. Fetch Global Invoices (Only Open/Draft Invoices)
198:     this.apiService.getInvoices(undefined, this.selectedCenterId || undefined).subscribe((d: any[]) => {
199:       this.globalInvoices = (d || []).filter(inv => inv.status === 'draft');
200:       this.cdr.detectChanges();
201:     });
202: 
203:     // 2. Fetch Appointments
204:     this.apiService.getAppointments(this.selectedCenterId || undefined).subscribe((d: any[]) => {
205:       this.appointments = d || [];
206:       this.cdr.detectChanges();
207:     });
208: 
209:     // 3. Fetch Staff Activity Today (using ServiceUsageReport)
210:     const today = new Date().toISOString().split('T')[0];
211:     this.apiService.getServiceUsageReport(this.selectedCenterId || undefined, today, today).subscribe((d: any[]) => {
212:       this.staffActivity = d || [];
213:       this.cdr.detectChanges();
214:     });
215:   }
216: 
217:   loadMasters() {
218:     const cid = this.selectedCenterId ?? undefined;
219:     this.apiService.getServices(cid).subscribe((d: any[]) => this.services = d || []);
220:     this.apiService.getProducts(cid).subscribe((d: any[]) => this.products = d || []);
221:     this.apiService.getMemberships(cid).subscribe((d: any[]) => this.memberships = d || []);
222:     this.apiService.getPackages(cid).subscribe((d: any[]) => this.packages = d || []);
223:     this.apiService.getValueCards(cid).subscribe((d: any[]) => this.cards = d || []);
224:     this.apiService.getStaffMembers(cid).subscribe((d: any[]) => {
225:       this.staffMembers = (d || []).filter((s: any) => s.is_active !== false);
226:       this.cdr.detectChanges();
227:     });
228:     this.apiService.get('marketing/api/promotions/').subscribe((d: any[]) => this.promotions = d || []);
229: 
230:   }
231: 
232:   loadClients() {
233:     this.apiService.getClients('').subscribe((d: any[]) => {
234:       this.clients = d || [];
235:       this.cdr.detectChanges();
236:     }, (err: any) => {
237:       console.error('Failed to load clients', err);
238:     });
239:   }
240: 
241:   // --- View Mode Toggles ---
242:   openNewInvoice() {
243:     this.viewMode = 'new-invoice';
244:   }
245: 
246:   discardInvoice() {
247:     this.viewMode = 'landing';
248:     this.cart = [];
249:     this.client = null;
250:     this.searchPhone = '';
251:     this.currentInvoiceId = null;
252:     this.invoiceDiscount = 0;
253:     this.invoiceCGST = 0;
254:     this.invoiceSGST = 0;
255:     this.useAdvancePayment = false;
256:     this.loadLandingData();
257:   }
258: 
259:   onSearchPhoneChange() {
260:     this.clients = [];
261:   }
262: 
263:   // --- Client Search & Select ---
264:   searchClients() {
265:     console.log('Searching clients for', this.searchPhone, 'globally');
266:     this.apiService.getClients(this.searchPhone).subscribe((d: any[]) => {
267:       console.log('Clients response', d);
268:       this.clients = d || [];
269:       this.cdr.detectChanges();
270:     }, (err: any) => {
271:       console.error('Clients API error', err);
272:     });
273:   }
274: 
275:   selectClient(client: any) {
276:     this.client = client;
277:     this.searchPhone = client.phone;
278:     this.clients = [];
279:     this.loadClientHistory(client.id);
280:     this.loadClientAdvances(client.id);
281:     
282:     // Inject Active Memberships into Promotions
283:     if (this.client.active_memberships && this.client.active_memberships.length > 0) {
284:         this.client.active_memberships.forEach((am: any) => {
285:             if (am.membership_detail) {
286:                 const exists = this.promotions.find((p: any) => p.id === 'm_' + am.id);
287:                 if (!exists) {
288:                     this.promotions.push({
289:                         id: 'm_' + am.id,
290:                         name: '👑 ' + am.membership_detail.name,
291:                         discount_percent: am.membership_detail.discount_percent,
292:                         discount_type: 'Percentage'
293:                     });
294:                 }
295:             }
296:         });
297:     }
298: 
299:     // Inject Active Packages into Services (Redeem for Rs. 0)
300:     if (this.client.active_packages && this.client.active_packages.length > 0) {
301:         this.client.active_packages.forEach((ap: any) => {
302:             if (ap.package_detail && ap.services_remaining) {
303:                 Object.keys(ap.services_remaining).forEach(svcId => {
304:                     const remaining = ap.services_remaining[svcId];
305:                     if (remaining > 0) {
306:                         const originalSvc = this.services.find(s => s.id === Number(svcId));
307:                         if (originalSvc) {
308:                             // Add a zero-cost redeemable service to the list
309:                             const redeemSvc = { ...originalSvc };
310:                             redeemSvc.name = `🎁 [Redeem] ${originalSvc.name} (${remaining} left)`;
311:                             redeemSvc.price = 0;
312:                             redeemSvc.default_price = 0;
313:                             this.services.unshift(redeemSvc);
314:                         }
315:                     }
316:                 });
317:             }
318:         });
319:     }
320:   }
321: 
322:   loadClientHistory(clientId: number) {
323:     this.apiService.get(`billing/invoices/?client_id=${clientId}`).subscribe((data: any) => {
324:       this.clientInvoices = data;
325:       this.buildClientHistory();
326:     });
327:   }
328: 
329:   loadClientAdvances(clientId: number) {
330:     this.apiService.get(`billing/advances/?client_id=${clientId}`).subscribe((data: any) => {
331:       this.clientAdvances = data;
332:       this.clientAdvanceBalance = data.reduce((sum: number, adv: any) => sum + parseFloat(adv.amount), 0);
333:       this.buildClientHistory();
334:     });
335:   }
336: 
337:   buildClientHistory() {
338:     const history = [];
339:     for (const inv of this.clientInvoices) {
340:       history.push({
341:         type: 'Invoice',
342:         center: inv.client?.center_detail?.display_name || 'All Centers',
343:         date: new Date(inv.created_at),
344:         ref: inv.id,
345:         amount: inv.total_amount
346:       });
347:     }
348:     for (const adv of this.clientAdvances) {
349:       history.push({
350:         type: 'Advance',
351:         center: adv.client?.center_detail?.display_name || 'All Centers',
352:         date: new Date(adv.created_at),
353:         ref: adv.id,
354:         amount: adv.amount
355:       });
356:     }
357:     history.sort((a, b) => b.date.getTime() - a.date.getTime());
358:     this.clientHistory = history;
359: 
360:     // Auto-detect membership based on true active status
361:     if (this.client && this.client.active_memberships && this.client.active_memberships.length > 0) {
362:       const am = this.client.active_memberships[0];
363:       const promoId = 'm_' + am.id;
364:       const promo = this.promotions.find((p: any) => p.id === promoId);
365:       if (promo) {
366:         this.selectedPromotion = promo;
367:         this.applyPromotion();
368:       }
369:     }
370: 
371:   }
372: 
373:   newClient() {
374:     let defaultCenter = this.selectedCenterId;
375:     if (!defaultCenter && this.centers && this.centers.length > 0) {
376:        defaultCenter = this.centers[0].id;
377:     }
378:     this.client = {
379:       phone: this.searchPhone || '',
380:       app_pin: '',
381:       first_name: '',
382:       last_name: '',
383:       email: '',
384:       birthday: '',
385:       gst_number: '',
386:       notes: '',
387:       dnd_status: 'NOT ON DND',
388:       center: defaultCenter,
389:       gender: 'female'
390:     };
391:   }
392: 
393:   saveClient() {
394:     if (!this.client) {
395:       return;
396:     }
397:     if (!this.client.first_name || !this.client.phone) {
398:       alert('First Name and Phone Number are required to save a client.');
399:       return;
400:     }
401:     if (this.client.id) {
402:       this.apiService.updateClient(this.client.id, this.client).subscribe(() => {
403:         alert('Client updated');
404:       });
405:     } else {
406:       this.apiService.createClient(this.client).subscribe((res: any) => {
407:         this.client = res;
408:         alert('Client created');
409:       }, (err: any) => {
410:         alert('Failed to create client. Please check details.');
411:         console.error(err);
412:       });
413:     }
414:   }
415: 
416:   // --- UI Tabs ---
417:   customPackageObj = { name: 'Custom Package', isCustom: true };
418: 
419:   setActiveTab(tab: 'search' | 'cards' | 'packages' | 'memberships' | 'advance') {
420:     this.activeTab = tab;
421:     if (tab === 'search') {
422:       this.selectedItemForConfig = null;
423:       this.configType = null;
424:     } else if (tab === 'cards') {
425:       this.configType = 'card';
426:       this.selectedItemForConfig = this.cards.length > 0 ? this.cards[0] : {};
427:     } else if (tab === 'packages') {
428:       this.configType = 'package';
429:       this.selectedItemForConfig = this.customPackageObj;
430:       this.onPackageSelectionChange();
431:     } else if (tab === 'memberships') {
432:       this.configType = 'membership';
433:       this.selectedItemForConfig = this.memberships.length > 0 ? this.memberships[0] : {};
434:     } else if (tab === 'advance') {
435:       this.configType = 'advance';
436:       this.selectedItemForConfig = { isAdvance: true };
437:     }
438:   }
439: 
440:   onPackageSelectionChange() {
441:     this.packageSelectedServices = [];
442:     this.finalConfigPrice = 0;
443:     this.packageSearchTerm = '';
444:     
445:     if (this.selectedItemForConfig && this.selectedItemForConfig.id) {
446:        this.finalConfigPrice = this.selectedItemForConfig.price || 0;
447:        if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {
448:            this.packageSelectedServices = this.selectedItemForConfig.services_json.map((s: any) => ({
449:                id: s.service_id,
450:                name: s.service_name,
451:                price: s.price || 0,
452:                pkgQty: s.quantity || 1
453:            }));
454:        }
455:     }
456:   }
457: 
458:   get filteredServices() {
459:     const search = this.searchServiceTerm.toLowerCase();
460:     if (!search) return [];
461:     return this.services.filter((item: any) => item.name?.toLowerCase().includes(search));
462:   }
463: 
464:   get filteredProducts() {
465:     const search = this.searchProductTerm.toLowerCase();
466:     if (!search) return [];
467:     return this.products.filter((item: any) => item.name?.toLowerCase().includes(search));
468:   }
469: 
470:   get filteredMemberships() {
471:     return this.memberships.filter(m => m.is_active !== false);
472:   }
473: 
474:   get filteredPackages() {
475:     return this.packages.filter(p => p.is_active !== false);
476:   }
477: 
478:   get filteredCards() {
479:     return this.cards.filter(c => c.is_active !== false);
480:   }
481: 
482:   get filteredPromotions() {
483:     return this.promotions.filter(p => p.is_active !== false);
484:   }
485: 
486:   
487:   getEffectivePrice(item: any): number {
488:     if (!item) return 0;
489:     const overridePrice = item?.center_override?.price;
490:     const directPrice = item?.price ?? item?.default_price ?? item?.selling_price ?? item?.price_amount ?? item?.value;
491:     const price = (overridePrice !== undefined && overridePrice !== null) ? overridePrice : directPrice;
492:     const numeric = Number(price);
493:     return !isNaN(numeric) ? numeric : 0;
494:   }
495: 
496: 
497: 
498:   
499:   isStaffSelected(id: any): boolean {
500:     return this.configStaffIds.includes(Number(id));
501:   }
502:   toggleStaffSelection(id: any) {
503:     const numId = Number(id);
504:     if (this.configStaffIds.includes(numId)) {
505:       this.configStaffIds = this.configStaffIds.filter(x => x !== numId);
506:     } else {
507:       this.configStaffIds = [...this.configStaffIds, numId];
508:     }
509:   }
510: 
511: 
512:   applyPromotion() {
513:     if (!this.selectedPromotion) {
514:        this.invoiceDiscount = 0;
515:        return;
516:     }
517:     let discount = 0;
518:     if (this.selectedPromotion.discount_percent) { // It's a membership
519:        discount = (this.subtotalAmount * this.selectedPromotion.discount_percent) / 100;
520:     } else if (this.selectedPromotion.discount_type === 'Percentage') {
521:        discount = (this.subtotalAmount * this.selectedPromotion.discount_value) / 100;
522:     } else if (this.selectedPromotion.discount_type === 'Flat') {
523:        discount = this.selectedPromotion.discount_value;
524:     }
525:     // Cap discount at subtotal to avoid negative totals
526:     if (discount > this.subtotalAmount) {
527:        discount = this.subtotalAmount;
528:     }
529:     this.invoiceDiscount = discount;
530:   }
531:   
532:   openCheckoutModal() {
533:     if (!this.client || !this.client.id) {
534:       alert('Please select or create a client first.');
535:       return;
536:     }
537:     const missingStaff = this.cart.some((c: any) => !c.staff_members || c.staff_members.length === 0);
538:     if (missingStaff) {
539:       alert('Please select at least one staff member for each item before finalizing.');
540:       return;
541:     }
542:     this.applyPromotion(); // Re-apply to ensure exact math
543:     
544:     this.checkoutPayments = [{ method: 'Cash', amount: this.finalTotalAmount }];
545:     this.showCheckoutModal = true;
546:     this.calcCheckoutRemaining();
547:   }
548:   
549:   addPaymentRow() {
550:     this.checkoutPayments.push({ method: 'UPI', amount: 0 });
551:     this.calcCheckoutRemaining();
552:   }
553:   removePaymentRow(index: number) {
554:     this.checkoutPayments.splice(index, 1);
555:     this.calcCheckoutRemaining();
556:   }
557:   
558:   calcCheckoutRemaining() {
559:     let sum = 0;
560:     this.checkoutPayments.forEach(p => sum += Number(p.amount || 0));
561:     this.checkoutRemaining = this.finalTotalAmount - sum;
562:   }
563:   
564:   closeCheckoutModal() {
565:     this.showCheckoutModal = false;
566:   }
567: 
568:   // --- Cart & Invoice Logic ---
569:   openConfig(item: any, type: 'service' | 'product' | 'card' | 'advance' | 'package' | 'membership') {
570:     this.selectedItemForConfig = item;
571:     this.configType = type;
572:     this.resetConfig();
573:   }
574: 
575:   resetConfig() {
576:     this.managerDiscountPercent = 0;
577:     this.managerDiscountAmount = 0;
578:     this.configStaffIds = [];
579:     if (this.selectedItemForConfig && (this.configType === 'service' || this.configType === 'product')) {
580:       this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
581:     } else if (this.selectedItemForConfig) {
582:        this.finalConfigPrice = this.selectedItemForConfig.price || 0;
583:        if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {
584:            this.packageSelectedServices = this.selectedItemForConfig.services_json.map((s: any) => ({
585:                id: s.service_id,
586:                name: s.service_name,
587:                price: s.price || 0,
588:                pkgQty: s.quantity || 1
589:            }));
590:        }
591:     }
592:   }
593: 
594:   recalcConfigPrice() {
595:     if (!this.selectedItemForConfig) return;
596:     const base = this.getEffectivePrice(this.selectedItemForConfig);
597:     const afterPct = base - (base * (this.managerDiscountPercent / 100));
598:     this.finalConfigPrice = afterPct - this.managerDiscountAmount;
599:   }
600: 
601:   confirmAddToCart() {
602:     if (this.configType === 'advance') {
603:       const entry = {
604:         content_type: 'advance',
605:         object_id: null,
606:         description: this.advanceDescription || 'Advance Payment',
607:         unit_price: this.advanceAmount || 0,
608:         discount: 0,
609:         quantity: 1,
610:         staff: null
611:       };
612:       this.cart.push(entry);
613:     } else if (this.selectedItemForConfig) {
614:       // Map frontend configType to backend content_type
615:       let ct = 'services.servicemaster';
616:       if (this.configType === 'product') ct = 'inventory.product';
617:       else if (this.configType === 'card') ct = 'marketing.card';
618:       else if (this.configType === 'package') ct = 'marketing.package';
619:       else if (this.configType === 'membership') ct = 'marketing.membership';
620: 
621:       const basePrice = this.getEffectivePrice(this.selectedItemForConfig);
622:       const discount = basePrice - this.finalConfigPrice;
623: 
624:       const entry = {
625:         content_type: ct,
626:         object_id: this.selectedItemForConfig.id,
627:         description: this.selectedItemForConfig.name || this.selectedItemForConfig.title || 'Item',
628:         unit_price: basePrice,
629:         discount: discount > 0 ? discount : 0,
630:         quantity: 1,
631:         staff_members: [...this.configStaffIds]
632:       };
633:       this.cart.push(entry);
634:     }
635:     this.packageSelectedServices = [];
636:     
637:     // Reset state after adding
638:     this.selectedItemForConfig = null;
639:     this.configType = null;
640:     this.activeTab = 'search';
641:     this.advanceAmount = 0;
642:     this.advanceDescription = '';
643:   }
644: 
645:   get packageFilteredServices() {
646:     const term = this.packageSearchTerm.toLowerCase();
647:     if (!term) return [];
648:     return this.services.filter(s => s.name?.toLowerCase().includes(term));
649:   }
650: 
651:   addServiceToPackage(service: any) {
652:     this.packageSelectedServices.push({ ...service, pkgQty: 1 });
653:     this.packageSearchTerm = '';
654:   }
655: 
656:   removeServiceFromPackage(index: number) {
657:     this.packageSelectedServices.splice(index, 1);
658:   }
659: 
660:   getStaffName(staffId: number | string): string {
661:     const st = this.staffMembers.find((s: any) => s.id == staffId);
662:     return st ? `${st.first_name} ${st.last_name || ''}`.trim() : 'Unknown Staff';
663:   }
664: 
665:   removeFromCart(i: number) {
666:     this.cart.splice(i, 1);
667:   }
668: 
669:   get subtotalAmount() {
670:     return this.cart.reduce((s: any, c: any) => s + ( (Number(c.unit_price || 0) * Number(c.quantity || 1)) - Number(c.discount || 0) ), 0);
671:   }
672:   
673:   get totalItemDiscount() {
674:     return this.cart.reduce((s: any, c: any) => s + Number(c.discount || 0), 0) + Number(this.invoiceDiscount || 0);
675:   }
676: 
677:   get finalTotalAmount() {
678:     let sub = this.subtotalAmount - Number(this.invoiceDiscount || 0);
679:     let totalTax = Number(this.invoiceCGST || 0) + Number(this.invoiceSGST || 0);
680:     return Math.round(sub + totalTax); // Rounding applied natively
681:   }
682:   
683:   get roundingAmount() {
684:     let sub = this.subtotalAmount - Number(this.invoiceDiscount || 0);
685:     let totalTax = Number(this.invoiceCGST || 0) + Number(this.invoiceSGST || 0);
686:     let exact = sub + totalTax;
687:     return Math.round(exact) - exact;
688:   }
689: 
690:   saveInvoice(onHold: boolean) {
691:     if (!this.client || !this.client.id) {
692:       alert('Please select or create a client first.');
693:       return;
694:     }
695: 
696:     if (!onHold && this.useAdvancePayment) {
697:        if (this.clientAdvanceBalance < this.finalTotalAmount) {
698:            alert("Insufficient Advance Balance to cover the total amount.");
699:            return;
700:        }
701:     }
702: 
703:     
704:     
705: 
706:     
707:     const payload: any = {
708:       client: this.client.id,
709:       center: this.selectedCenterId,
710:       notes: '',
711:       subtotal: this.subtotalAmount,
712:       discount: this.invoiceDiscount,
713:       cgst: this.invoiceCGST,
714:       sgst: this.invoiceSGST,
715:       rounding: this.roundingAmount,
716:       total_amount: this.finalTotalAmount,
717:       paid_amount: onHold ? 0 : this.finalTotalAmount,
718:       status: onHold ? 'draft' : 'paid',
719:       payments: onHold ? [] : this.checkoutPayments,
720:       items: this.cart.map((c: any) => {
721:         return {
722:           content_type: c.content_type,
723:           object_id: c.object_id,
724:           description: c.description,
725:           unit_price: c.unit_price,
726:           discount: c.discount,
727:           quantity: c.quantity,
728:           staff_members: c.staff_members
729:         };
730:       })
731:     };
732: 
733:     
734:     if (this.currentInvoiceId) {
735:       this.apiService.put(`billing/invoices/${this.currentInvoiceId}/`, payload).subscribe({
736:         next: (res: any) => {
737:           alert('Invoice updated successfully!');
738:           this.handlePostSave(onHold, res);
739:         },
740:         error: (err: any) => {
741:           alert('Failed to update invoice');
742:           console.error(err);
743:         }
744:       });
745:     } else {
746:       this.apiService.post(`billing/invoices/`, payload).subscribe({
747:         next: (res: any) => {
748:           alert('Invoice generated successfully!');
749:           this.handlePostSave(onHold, res);
750:         },
751:         error: (err: any) => {
752:           alert('Failed to create invoice');
753:           console.error(err);
754:         }
755:       });
756:     }
757:   }
758: 
759:   handlePostSave(onHold: boolean, invoice: any) {
760:     this.closeCheckoutModal();
761:     const advanceItem = this.cart.find(it => it.content_type === 'advance');
762:     if (!onHold && advanceItem) {
763:         this.apiService.post(`billing/advances/`, {
764:             client: this.client.id,
765:             amount: advanceItem.unit_price * advanceItem.quantity,
766:             notes: advanceItem.description || 'Advance Payment'
767:         }).subscribe(() => {
768:             this.discardInvoice();
769:         });
770:     } else {
771:         this.discardInvoice();
772:     }
773:   }
774: 
775: 
776:   loadInvoice(invoice: any) {
777:     if (invoice.status !== 'draft') {
778:       alert('Can only load open (draft) invoices.');
779:       return;
780:     }
781:     this.viewMode = 'new-invoice';
782:     this.currentInvoiceId = invoice.id;
783:     
784:     
785:     // Assuming backend returns client details. If just ID, fetch client.
786:     if (invoice.client) {
787:        // Just fetch it by ID to be safe and populate all fields
788:        const clientId = typeof invoice.client === 'object' ? invoice.client.id : invoice.client;
789:        this.apiService.getClients(clientId.toString()).subscribe((d: any[]) => {
790:           const c = (d||[]).find(x => x.id === clientId);
791:           if (c) this.selectClient(c);
792:        });
793:     }
794: 
795:     this.cart = [];
796:     if (invoice.items) {
797:       invoice.items.forEach((it: any) => {
798:          this.cart.push({
799:            content_type: it.content_type,
800:            object_id: it.object_id,
The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.
