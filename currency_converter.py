# encoding: utf-8
import argparse
import requests
import json


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Convert value to other currencies.'
    )
    parser.add_argument(
        '--amount',
        dest='amount',
        required=True,
        type=float,
        help='Amount to convert'
    )
    parser.add_argument(
        '--input_currency',
        dest='input_currency',
        required=True,
        type=str,
        help='Amount to convert'
    )
    parser.add_argument(
        '--output_currency',
        dest='output_currency',
        type=str,
        help='Amount to convert'
    )
    args = parser.parse_args()
    return args


class CurrencyConverter:

    # resolve ambiguous currency symbols
    KNOWN_SYMBOLS_MAP = {
        '$': 'USD',
        'kr': 'SEK',
        '£': 'GBP',
        '¥': 'JPY',
        'ƒ': 'AWG',
        'лв': 'BGN',
        '₨': 'PKR',
        '₩': 'KRW',
        '﷼': 'IRR'
    }

    def __init__(
            self,
            amount: float,
            input_currency: str,
            output_currency: str
    ):
        self.amount = amount
        self.input_currency = input_currency
        self.output_currency = output_currency
        self.__currencies_by_id = None
        self.__currencies_by_symbol = None

    def __fill_currency_maps(self):
        # TODO: this public API is limited by 100 requests per hour,
        # need to find public API with unlimited access (parse Wikipedia maybe?)
        fetch_results = requests.get(
            'http://free.currencyconverterapi.com/api/v3/currencies'
        ).json()['results']
        self.__currencies_by_id = fetch_results
        self.__currencies_by_symbol = {
            fetch_results[k].get('currencySymbol'): k
            for k in fetch_results
        }

        # force fill map for ambiguous symbols
        for known_symbol in self.KNOWN_SYMBOLS_MAP:
            self.__currencies_by_symbol[known_symbol] = \
                self.__currencies_by_id[self.KNOWN_SYMBOLS_MAP[known_symbol]]

    @property
    def currencies_by_id(self)->dict:
        if self.__currencies_by_id is None:
            self.__fill_currency_maps()
        return self.__currencies_by_id

    @property
    def currencies_by_symbol(self)->dict:
        if self.__currencies_by_symbol is None:
            self.__fill_currency_maps()
        return self.__currencies_by_symbol

    def __detect_currency_id(self, currency: str):
        if currency in self.currencies_by_id:
            return currency
        if currency in self.currencies_by_symbol:
            return self.currencies_by_symbol[currency]['id']
        raise ValueError('Unknown currency passed as parameter: {}'.format(
            currency
        ))

    def __compose_yql_text(self):
        if self.output_currency:
            pairs_text = "'{}{}'".format(
                self.input_currency,
                self.output_currency
            )
        else:
            pairs_text = ','.join([
                "'{}{}'".format(self.input_currency, cur_id)
                for cur_id in self.currencies_by_id
            ])
        query_text = "https://query.yahooapis.com/v1/public/yql?q=select * " \
                     "from yahoo.finance.xchange where pair in ({})" \
                     "&format=json&env=store://datatables.org/alltableswithkeys"
        query_text = query_text.format(pairs_text)
        return query_text

    def __compose_result_from_yahoo_response(self, yahoo_response):
        rates = yahoo_response['query']['results']['rate']
        if not isinstance(rates, list):
            rates = [rates]
        output = {}
        for rate in rates:
            currency_id = rate['id'][3:]
            try:
                amount = round(float(rate['Ask']) * self.amount, 2)
                output[currency_id] = amount
            except ValueError:
                pass
        result = {
            'input': {
                'amount': self.amount,
                'currency': self.input_currency
            },
            'output': output
        }
        return json.dumps(result, indent=4)

    def run(self):
        self.input_currency = self.__detect_currency_id(self.input_currency)
        if self.output_currency:
            self.output_currency = self.__detect_currency_id(
                self.output_currency
            )
        yahoo_response = requests.get(
            self.__compose_yql_text()
        ).json()
        return self.__compose_result_from_yahoo_response(yahoo_response)


def main():
    options = parse_arguments()

    converter = CurrencyConverter(
        options.amount,
        options.input_currency,
        options.output_currency
    )
    result = converter.run()
    print(result)


if __name__ == '__main__':
    main()
