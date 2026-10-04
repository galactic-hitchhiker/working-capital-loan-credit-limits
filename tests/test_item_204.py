"""Check conservative event evidence and isolation of the filing section."""
import unittest
from mcf.enrichment.item204.classify import classify_item_204, extract_item_204, has_item, matches


class Item204Tests(unittest.TestCase):
    def test_payment_failure(self):
        self.assertEqual(classify_item_204('The company failed to pay interest.'), 'QUALIFIED_DEFAULT')

    def test_generic_default_requires_review(self):
        self.assertEqual(classify_item_204('An event of default has occurred.'), 'MANUAL_REVIEW')

    def test_strong_without_actual_requires_review(self):
        self.assertEqual(classify_item_204('Payment default may constitute a breach.'), 'MANUAL_REVIEW')

    def test_hypothetical_payment_failure_requires_review(self):
        self.assertEqual(classify_item_204('A technical default may result if the borrower failed to pay.'), 'MANUAL_REVIEW')

    def test_technical_and_redemption(self):
        for text in ('A covenant violation occurred.', 'Scheduled redemption.', 'A technical event of default.'):
            self.assertEqual(classify_item_204(text), 'NON_DEFAULT')

    def test_hypothetical(self):
        self.assertEqual(classify_item_204('This could constitute a breach.'), 'NON_DEFAULT')

    def test_foreclosure(self):
        self.assertEqual(classify_item_204('The lender commenced foreclosure.'), 'QUALIFIED_DEFAULT')

    def test_ambiguous_or_negated_events(self):
        for text in (
            'No payment default has occurred.',
            'The debt was not accelerated.',
            'The lender may commence foreclosure.',
            'If the company failed to pay interest, acceleration would follow.',
            'A covenant violation occurred. Payment default may result.',
            'The lender received notice of a possible foreclosure.',
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_item_204(text), 'MANUAL_REVIEW')

    def test_nonfinancial_failure(self):
        self.assertEqual(classify_item_204('The company failed to make a filing.'), 'MANUAL_REVIEW')

    def test_realized_financial_events(self):
        for text in (
            'The company missed an interest payment.',
            'Principal has not been paid.',
            'The notes have been accelerated.',
            'The lender declared the loan immediately due and payable.',
            "The trustee’s sale was completed.",
            'A covenant violation occurred. The company failed to pay principal.',
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_item_204(text), 'QUALIFIED_DEFAULT')

    def test_conditional_line_breaks_and_disputes(self):
        for text in (
            'If the company\nfailed to pay interest, the lender could accelerate.',
            'If a default occurs; the debt was accelerated under the agreement.',
            'The company disputes that a payment default has occurred.',
            'The company hasn’t failed to pay interest.',
            'An event of default occurred and may result in acceleration.',
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_item_204(text), 'MANUAL_REVIEW')

    def test_additional_nonpayment_wording(self):
        for text in ('The company did not pay interest.',
                     'Scheduled payments have not been paid.',
                     'The company failed to make a principal payment.'):
            with self.subTest(text=text):
                self.assertEqual(classify_item_204(text), 'QUALIFIED_DEFAULT')

    def test_month_may_is_not_hypothetical(self):
        self.assertEqual(
            classify_item_204(
                'On May 5, 2023, the Company failed to make payment of principal and interest.'
            ),
            'QUALIFIED_DEFAULT',
        )

    def test_unrelated_payment_word_does_not_qualify(self):
        self.assertEqual(classify_item_204(
            'The company failed to make a filing concerning interest payments.'
        ), 'MANUAL_REVIEW')

    def test_case_insensitive_dotall(self):
        self.assertIs(matches([r'declared.{0,50}immediately due'], 'DECLARED\n immediately due'), True)
        self.assertIs(matches([r'failed'], 'Nothing relevant'), False)

    def test_exact_item(self):
        self.assertTrue(has_item('1.01; 2.04,9.01', '2.04'))
        self.assertFalse(has_item('12.04', '2.04'))

    def test_section_isolation(self):
        try:
            import bs4
        except ImportError:
            self.skipTest('Install mcf/enrichment/item204/requirements.txt for HTML parser tests')
        html = '<p>Item 1.01 The company failed to pay.</p><p>Item 2.04 ' + 'A covenant breach occurred. ' * 8 + '</p><p>Item 9.01 Exhibits</p>'
        text, status = extract_item_204(html)
        self.assertEqual(status, 'isolated_item_section')
        self.assertNotIn('failed to pay', text)
        self.assertEqual(classify_item_204(text), 'NON_DEFAULT')


if __name__ == '__main__':
    unittest.main()
