import argparse
import pandas as pd
from scipy.stats import gmean

from bokeh.plotting import figure
from bokeh.io import curdoc, output_file, save
from bokeh.resources import CDN
from bokeh.embed import file_html, components
from bokeh.layouts import row
from bokeh.models import HoverTool

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--static', action='store_true',
                        default=False,
                        help="save a full html file")

    args = parser.parse_args()
    args.words_per_chunk = 140
    args.data_path = 'fandom-data.csv'
    title = 'Average Quantity of Text Reuse by {}-word Section'
    title = title.format(args.words_per_chunk)
    args.title = title
    args.out_filename = 'star-wars-reuse.html'
    return args

def word_formatter(names=None):
    if names is None:
        names = []

    punctuation = [',', '.', '!', '?', '\'', '"', ':', '-', '--']
    endpunctuation = ['.', '!', '?', '"', '...', '....', '--']
    contractions = ['\'ve', '\'m', '\'ll', '\'re', '\'s', '\'t', 'n\'t', 'na']
    capitals = ['i']

    def span(content, highlight=None):
        if highlight is None:
            return '<span>{}</span>'.format(content)
        else:
            style = 'background-color: rgba(16, 96, 255, {:04.3f})'.format(highlight)
            return '<span style="{}">{}</span>'.format(style, content)

    def format_word(word, prev_word, character, new_char, new_scene, highlight=None):
        parts = []
        if new_scene:
            parts.append(span('-- next scene--<br \>'))
        if new_char:
            parts.append('\n')
            parts.append(span(' ' + character.upper() + ': '))

        if word in punctuation or word in contractions:
            # no space before punctuation
            parts.append(span(word, highlight))
        elif not prev_word or prev_word in endpunctuation:
            # capitalize first word of sentence
            parts.append(span(' ' + word.capitalize(), highlight))
        elif word in capitals:
            # format things like 'i'
            parts.append(span(' ' + word.upper(), highlight))
        elif word.capitalize() in names:
            # format names
            parts.append(span(' ' + word.capitalize(), highlight))
        else:
            # all other words
            parts.append(span(' ' + word, highlight))
        return ''.join(parts)
    return format_word

def chart_cols(fandom_data, words_per_chunk):
    words = fandom_data['LOWERCASE'].tolist()
    prevwords = [None] + words[:-1]
    chars = fandom_data['CHARACTER'].tolist()
    newchar = fandom_data['CHARACTER'][:-1].values != fandom_data['CHARACTER'][1:].values
    newchar = [True] + list(newchar)
    newscene = fandom_data['SCENE'][:-1].values != fandom_data['SCENE'][1:].values
    newscene = [False] + list(newscene)


    highlights = fandom_data['Frequency of Reuse (Exact)'].tolist()
    chunks = (fandom_data.index // words_per_chunk).tolist()
    chunkmax = {}
    for h, c in zip(highlights, chunks):
        if c not in chunkmax or chunkmax[c] < h:
            chunkmax[c] = h
    highlights = [h / chunkmax[c] for h, c in zip(highlights, chunks)]

    wform = word_formatter()
    spans = list(map(wform, words, prevwords, chars, newchar, newscene, highlights))

    chart_cols = fandom_data[['Frequency of Reuse (Exact)']]
    chart_cols = chart_cols.assign(chunk=chunks)
    chart_cols = chart_cols.assign(span=spans)

    return chart_cols

def join_wrap(seq):
    lines = []
    line = []
    last_br = 0
    for span in seq:
        if '\n' in span or last_br > 7 and '> ' in span:
            # Convert newlines to div breaks. Also insert breaks
            # whenever we've seen 7 words and there is some
            # leading whitespace in the current span.
            lines.append(''.join(line))
            line = []
            last_br = 0
        else:
            last_br += 1

        line.append(span)

    tail = ''.join(line)
    if tail.strip():
        lines.append(tail)

    return '\n'.join('<div>{}</div>'.format(l) for l in lines)

def chart_pivot(chart_cols):
    return pd.pivot_table(
        chart_cols,
        values=['Frequency of Reuse (Exact)', 'span'],
        index=chart_cols.chunk,
        aggfunc={
            'Frequency of Reuse (Exact)': lambda x: gmean(x + 1),
            'span': join_wrap
        }
    )

def build_plot(data_path, words_per_chunk, title='Reuse'):
    fd = pd.read_csv(data_path)
    cc = chart_cols(fd, words_per_chunk)
    freq = chart_pivot(cc)
    plot = figure(plot_width=800, plot_height=600,
                  title=title, tools="hover")
    hover = plot.select(dict(type=HoverTool))
    hover.tooltips = "<div>@span{safe}</div>"
    plot.vbar(x="chunk",
              width=0.75,
              bottom=0,
              source=freq,
              top="Frequency of Reuse (Exact)",
              color="#CAB2D6")
    return plot


if __name__ == '__main__':
    args = parse_args()
    p = build_plot(args.data_path, args.words_per_chunk)
    if args.static:
        html = file_html(p, CDN, args.title)
        output_file(args.out_filename,
                    title=args.title, mode="cdn")
        save(p)
    else:
        with open(args.out_filename, 'w', encoding='utf-8') as op:
            for c in components(p):
                op.write(c)
                op.write('\n')
else:
    args = parse_args()
    p = build_plot(args.data_path, args.words_per_chunk)
    layout = row(p)
    curdoc().add_root(layout)
    curdoc().title = args.title
