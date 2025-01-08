@app.route('/purchase/<int:event_id>', methods=['GET', 'POST'])
@app.route('/purchase/<int:event_id>/<string:promo_code>', methods=['GET', 'POST'])
def purchase(event_id, promo_code=None):
    try:
        event = Event.query.get_or_404(event_id)
        organizer = User.query.get(event.user_id)
        
        # Initialize variables with safe defaults
        total_tickets_sold = db.session.query(
            func.sum(Attendee.tickets_purchased)
        ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0

        # Fetch ticket types
        ticket_types = event.ticket_types
        
        # Calculate available tickets for each ticket type
        for ticket_type in ticket_types:
            # Get sold count for this ticket type
            type_sold_count = Attendee.query.filter_by(
                event_id=event_id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'
            ).count() or 0
            
            # Set sold count
            ticket_type.sold_count = type_sold_count
            
            # Calculate available tickets
            if ticket_type.quantity is not None:
                # Individual ticket limit
                ticket_type.available = max(0, ticket_type.quantity - type_sold_count)
            elif not event.enforce_individual_ticket_limits and event.ticket_quantity is not None:
                # Event-wide limit
                ticket_type.available = max(0, event.ticket_quantity - total_tickets_sold)
            else:
                # No limit
                ticket_type.available = None

        # Calculate total available tickets for the event
        if not event.enforce_individual_ticket_limits and event.ticket_quantity is not None:
            tickets_available = max(0, event.ticket_quantity - total_tickets_sold)
        else:
            tickets_available = None
        
        # Assign the business logo URL to logo_url
        organizer.logo_url = organizer.business_logo_url
        # Initialize variables
        attendees = []
        total_amount = 0  # Total amount in pence
        line_items = []
        booking_fee_pence = 0  # Initialize booking fee
        total_tickets_requested = 0

        # Collect custom questions from event
        custom_questions = []
        for i in range(1, 11):
            question_text = getattr(event, f'custom_question_{i}')
            # Only add questions that have actual content
            if question_text and question_text.strip() and question_text.lower() not in ['none', 'null', '']:
                custom_questions.append({
                    'id': f'custom_{i}',
                    'question_text': question_text,
                    'question_type': 'text',
                    'required': True
                })

        # Collect default questions from organizer
        default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
        default_questions = [{
            'id': f'default_{dq.id}',
            'question_text': dq.question,
            'question_type': 'text',
            'required': True
        } for dq in default_questions_query if dq.question and dq.question.strip() and dq.question.lower() not in ['none', 'null', '']]

        # Combine all questions
        all_questions = default_questions + custom_questions

        if request.method == 'POST':
            try:
                session_id = str(uuid4())
                full_name = request.form.get('full_name')
                email = request.form.get('email')
                phone_number = request.form.get('phone_number')

                # Validate required fields
                if not all([full_name, email, phone_number]):
                    flash('Please fill in all required fields.')
                    return redirect(url_for('purchase', event_id=event_id))

                if organizer.terms and organizer.terms.lower() != 'none':
                    if not request.form.get('accept_organizer_terms'):
                        flash("You must accept the event organizer's Terms and Conditions.")
                        return redirect(url_for('purchase', event_id=event_id))

                if not request.form.get('accept_platform_terms'):
                    flash("You must accept the platform's Terms and Conditions.")
                    return redirect(url_for('purchase', event_id=event_id))

                # Initialize variables
                attendees = []
                total_amount = 0  # Total amount in pence
                line_items = []
                booking_fee_pence = 0  # Initialize booking fee
                total_tickets_requested = 0

                # Collect custom questions from event
                custom_questions = []
                for i in range(1, 11):
                    question = getattr(event, f'custom_question_{i}')
                    if question and question.lower() not in ['none', 'null', '']:  # Only add non-empty questions
                        custom_questions.append({
                            'id': i,
                            'question_text': question,
                            'question_type': 'text',  # Default to text type
                            'required': True  # Default to required
                        })

                # Collect default questions from organizer
                default_questions = DefaultQuestion.query.filter_by(user_id=organizer.id).all()
                default_questions = [{
                    'id': q.id,
                    'question_text': q.question,
                    'question_type': 'text',  # Default to text type
                    'required': True  # Default to required
                } for q in default_questions if q.question and q.question.strip() and q.question.lower() not in ['none', 'null', '']]

                # Collect quantities for each ticket type
                quantities = {}
                for ticket_type in ticket_types:
                    quantity_str = request.form.get(f'quantity_{ticket_type.id}', '0')
                    quantity = int(quantity_str)
                    quantities[ticket_type.id] = quantity
                    if quantity > 0:
                        total_tickets_requested += quantity

                        if event.enforce_individual_ticket_limits and ticket_type.quantity is not None:
                            # Check if requested quantity exceeds available tickets for this type
                            tickets_sold_type = Attendee.query.filter_by(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                payment_status='succeeded'
                            ).count()
                            tickets_remaining = ticket_type.quantity - tickets_sold_type
                            if quantity > tickets_remaining:
                                flash(f"Cannot purchase {quantity} tickets for {ticket_type.name}. Only {tickets_remaining} tickets are available.")
                                return redirect(url_for('purchase', event_id=event_id))
                        else:
                            # Will check total capacity later
                            pass

                # If individual ticket limits are not enforced, check total event capacity
                if not event.enforce_individual_ticket_limits:
                    total_tickets_sold = db.session.query(
                        func.sum(Attendee.tickets_purchased)
                    ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                    tickets_available = event.ticket_quantity - total_tickets_sold
                    if total_tickets_requested > tickets_available:
                        flash(f"Cannot purchase {total_tickets_requested} tickets. Only {tickets_available} tickets are available.")
                        return redirect(url_for('purchase', event_id=event_id))
                else:
                    # When individual ticket limits are enforced, tickets_available isn't used in the same way
                    tickets_available = None  # Or handle accordingly

                # Collect custom questions
                questions = all_questions
                attendee_answers = {}

                # Collect answers for each ticket
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    for i in range(quantity):
                        answers = {}
                        for question in questions:
                            answer_key = f"ticket_{ticket_type.id}_{i}_question_{question['id']}"
                            answer = request.form.get(answer_key)
                            if not answer:
                                flash(f'Please answer all questions for {ticket_type.name} Ticket {i + 1}.')
                                return redirect(url_for('purchase', event_id=event_id))
                            answers[question['id']] = answer
                        attendee_answers[(ticket_type.id, i)] = answers


                # Create Attendee entries and calculate amounts
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    if quantity > 0:
                        for i in range(quantity):
                            ticket_number = generate_unique_ticket_number()
                            answers = attendee_answers.get((ticket_type.id, i), {})

                            attendee = Attendee(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                ticket_answers=json.dumps(answers),
                                payment_status='pending',
                                full_name=full_name,
                                email=email,
                                phone_number=phone_number,
                                tickets_purchased=1,
                                ticket_price_at_purchase=ticket_type.price,
                                session_id=session_id,
                                created_at=datetime.now(timezone.utc),
                                ticket_number=ticket_number
                            )
                            db.session.add(attendee)
                            attendees.append(attendee)

                # Collect custom questions from event
                custom_questions = []
                for i in range(1, 11):
                    question = getattr(event, f'custom_question_{i}')
                    if question and question.lower() not in ['none', 'null', '']:  # Only add non-empty questions
                        custom_questions.append({
                            'id': i,
                            'question_text': question,
                            'question_type': 'text',  # Default to text type
                            'required': True  # Default to required
                        })

                # Collect default questions from organizer
                default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).all()
                default_questions = [{
                    'id': q.id,
                    'question_text': q.question,
                    'question_type': 'text',  # Default to text type
                    'required': True  # Default to required
                } for q in default_questions_query if q.question and q.question.strip() and q.question.lower() not in ['none', 'null', '']]
            

                # Get promo code from form and initialize active_promo
                submitted_promo_code = request.form.get('promo_code')
                active_promo = None
                discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()

                if submitted_promo_code:
                    # Find matching promo code discount rule
                    active_promo = DiscountRule.query.filter_by(
                        event_id=event_id,
                        discount_type='promo_code',
                        promo_code=submitted_promo_code
                    ).first()

                # Calculate base amount (in pence)
                print("\n=== PAYMENT CALCULATION DETAILS ===")
                print("Calculating base amount for tickets:")
                base_amount = 0
                total_tickets = 0
                for ticket_type_id, quantity in quantities.items():
                    if quantity > 0:
                        ticket_type = next(tt for tt in ticket_types if tt.id == ticket_type_id)
                        ticket_total = ticket_type.price * quantity * 100
                        print(f"- {ticket_type.name}: {quantity} x £{ticket_type.price:.2f} = £{ticket_total/100:.2f}")
                        base_amount += ticket_total
                        total_tickets += quantity  # Add this line
                print(f"Base amount before discounts: £{base_amount/100:.2f}")

                # Apply discount
                discount_amount = 0
                if active_promo:
                    print(f"\nApplying promo code discount:")
                    print(f"- Discount percentage: {active_promo.discount_percent}%")
                    discount_amount = base_amount * (active_promo.discount_percent / 100)
                    print(f"- Promo code discount amount: £{discount_amount/100:.2f}")
                else:
                    # Check other discount rules only if no promo code is active
                    print("\nChecking other discount rules:")
                    discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
                    
                    for rule in discount_rules:
                        if rule.discount_type != 'promo_code':  # Skip promo code rules
                            current_discount = 0
                            print(f"\nEvaluating {rule.discount_type} discount rule:")
                            print(f"- Discount percentage: {rule.discount_percent}%")
                            
                            if rule.discount_type == 'early_bird':
                                if rule.valid_until and datetime.now() < rule.valid_until:
                                    if not rule.max_early_bird_tickets or total_tickets <= rule.max_early_bird_tickets:
                                        current_discount = base_amount * (rule.discount_percent / 100)
                            
                            elif rule.discount_type == 'bulk' and total_tickets >= rule.min_tickets:
                                print(f"- Bulk discount applies ({total_tickets} tickets >= {rule.min_tickets} min tickets)")
                                if rule.apply_to == 'all':
                                    current_discount = base_amount * (rule.discount_percent / 100)
                                    print(f"- Applying {rule.discount_percent}% to all tickets")
                                else:  # 'additional'
                                    per_ticket_amount = base_amount / total_tickets
                                    additional_tickets = total_tickets - 1
                                    current_discount = (per_ticket_amount * additional_tickets) * (rule.discount_percent / 100)
                                    print(f"- Applying {rule.discount_percent}% to {additional_tickets} additional tickets")
                            
                            print(f"- Calculated discount: £{current_discount/100:.2f}")
                            # Keep the highest discount
                            if current_discount > discount_amount:
                                discount_amount = current_discount
                                print(f"- New highest discount: £{discount_amount/100:.2f}")

                # Apply the discount
                total_amount_pence = int(base_amount - discount_amount)
                print(f"\nAmount after discounts: £{total_amount_pence/100:.2f}")

                # Calculate fees and amounts first
                print("\n=== PAYMENT CALCULATION LOG ===")
                print("1. Base Calculations:")
                print(f"- Original ticket amount: £{total_amount_pence/100:.2f}")
                print(f"- Number of tickets: {total_tickets}")
                
                # 1. Calculate platform fee (30p per ticket)
                base_platform_fee = 30  # 30p per ticket
                total_base_platform_fee = base_platform_fee * total_tickets

                # 2. Calculate subtotal (tickets + platform fees)
                subtotal = total_amount_pence + total_base_platform_fee

                # 3. Calculate Stripe fees on the subtotal
                stripe_percentage = 0.014  # 1.4%
                stripe_fixed = 20  # 20p fixed fee
                stripe_percentage_fee = int(subtotal * stripe_percentage)
                total_stripe_fee = stripe_percentage_fee + stripe_fixed

                # 4. Total fee to retain (platform fee + stripe fees)
                total_platform_fee = total_base_platform_fee + total_stripe_fee

                print("\n2. Fee Breakdown:")
                print(f"- Ticket amount: £{total_amount_pence/100:.2f}")
                print(f"- Platform fee (£0.30 × {total_tickets}): £{total_base_platform_fee/100:.2f}")
                print(f"- Subtotal: £{subtotal/100:.2f}")
                print(f"- Stripe fee (1.4% + £0.20): £{total_stripe_fee/100:.2f}")
                print(f"- Total fees to retain: £{total_platform_fee/100:.2f}")

                # Add all fees as a single line item
                total_fee_per_ticket = (total_platform_fee + total_stripe_fee) // total_tickets
                line_items.append({
                    'price_data': {
                        'currency': 'gbp',
                        'unit_amount': base_platform_fee + (total_stripe_fee // total_tickets),  # Platform fee + share of Stripe fees
                        'product_data': {
                            'name': 'Booking & Processing Fee',
                            'description': 'Includes platform and payment processing fees',
                        },
                    },
                    'quantity': total_tickets,
                })

                # Calculate final total
                total_charge = sum(item['price_data']['unit_amount'] * item['quantity'] for item in line_items)
                print(f"\n=== FINAL BREAKDOWN ===")
                print(f"Customer pays: £{total_charge/100:.2f}")
                print(f"→ Ticket amount: £{total_amount_pence/100:.2f} (to organizer)")
                print(f"→ Total fees: £{total_platform_fee/100:.2f} (retained)")
                print("=== END CALCULATION ===\n")

                # Create Stripe checkout session
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    success_url=url_for('success', session_id=session_id, _external=True),
                    cancel_url=url_for('cancel', _external=True),
                    metadata={
                        'session_id': session_id,
                        'platform_fee': str(platform_fee_per_ticket * total_tickets),
                        'total_tickets': str(total_tickets)
                    },
                    payment_intent_data={
                        'application_fee_amount': platform_fee_per_ticket * total_tickets,  # Platform keeps all fees
                        'on_behalf_of': organizer.stripe_connect_id,
                        'transfer_data': {
                            'destination': organizer.stripe_connect_id,
                        },
                        'transfer_group': session_id,
                    },
                    billing_address_collection='required',
                    customer_email=email
                )
                
                print(f"Checkout session created: {checkout_session.id}")
                print(f"Redirecting to: {checkout_session.url}")
                
                # Important: Return the redirect response
                return redirect(checkout_session.url)

            except stripe.error.StripeError as e:
                app.logger.error(f"Stripe Error: {str(e)}")
                flash('An error occurred with the payment processor. Please try again.', 'error')
                return redirect(url_for('purchase', event_id=event_id))
                    
            except Exception as e:
                app.logger.error(f"Error creating checkout: {str(e)}")
                app.logger.error(traceback.format_exc())
                flash('An error occurred. Please try again.', 'error')
                return redirect(url_for('purchase', event_id=event_id))

        else:
            # Get active discount rules
            discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
            active_discount = None
            
            for rule in discount_rules:
                if rule.discount_type == 'early_bird':
                    if rule.valid_until and datetime.now() < rule.valid_until:
                        active_discount = {
                            'type': 'early_bird',
                            'percentage': rule.discount_percent,
                            'valid_until': rule.valid_until.isoformat(),
                            'max_tickets': rule.max_early_bird_tickets
                        }
                        break
                elif rule.discount_type == 'bulk':
                    if rule.min_tickets:  # Only set up bulk discount if min_tickets is set
                        active_discount = {
                            'type': 'bulk',
                            'percentage': rule.discount_percent,
                            'minTickets': rule.min_tickets,
                            'apply_to': rule.apply_to or 'all'  # Default to 'all' if apply_to is None
                        }
                        print(f"Found bulk discount rule: {active_discount}")
                        break
                elif rule.discount_type == 'promo_code':
                    active_discount = {
                        'type': 'promo_code',
                        'percentage': rule.discount_percent
                    }
                    break

            platform_terms_link = 'https://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Terms-of-Service-25th-October-2024.pdf'
            organizer_terms_link = organizer.terms if organizer.terms and organizer.terms.lower() != 'none' else None

            # Calculate tickets available for total capacity events
            if not event.enforce_individual_ticket_limits:
                total_tickets_sold = db.session.query(
                    func.sum(Attendee.tickets_purchased)
                ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                tickets_available = event.ticket_quantity - total_tickets_sold
            else:
                tickets_available = None

            # Get promo code from form (though on GET request, this will be None)
            submitted_promo_code = request.form.get('promo_code')
            active_promo = None

            if submitted_promo_code:
                # Find matching promo code discount rule
                active_promo = DiscountRule.query.filter_by(
                    event_id=event_id,
                    discount_type='promo_code',
                    promo_code=submitted_promo_code
                ).first()

            # Collect custom questions from event
            custom_questions = []
            for i in range(1, 11):
                question_text = getattr(event, f'custom_question_{i}')
                if question_text and question_text.lower() not in ['none', 'null', '']:
                    custom_questions.append({
                        'id': f'custom_{i}',
                        'question_text': question_text,
                        'question_type': 'text',
                        'required': True  # Adjust as needed
                    })

            # Collect default questions from organizer
            default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
            default_questions = [{
                'id': f'default_{dq.id}',
                'question_text': dq.question,
                'question_type': 'text',
                'required': True  # Adjust as needed
            } for dq in default_questions_query if dq.question and dq.question.strip() and dq.question.lower() not in ['none', 'null', '']]

            # Combine all questions
            all_questions = default_questions + custom_questions

            # Print questions for debugging
            print("Questions being passed to template:", all_questions)

            return render_template(
                'purchase.html',
                event=event,
                organizer=organizer,
                questions=all_questions,
                organizer_terms_link=organizer_terms_link,
                platform_terms_link=platform_terms_link,
                ticket_types=ticket_types,
                enforce_individual_ticket_limits=event.enforce_individual_ticket_limits,
                tickets_available=tickets_available,
                discount_config=active_discount
            )
                                
        

    except Exception as e:
        app.logger.error(f"Error in purchase route: {str(e)}")
        app.logger.error(f"Event ID: {event_id}")
        # Add more detailed error logging
        import traceback
        app.logger.error(traceback.format_exc())
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))