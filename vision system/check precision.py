import pandas as pd
import pylab as plt
import numpy as np

def is_outlier(points, thresh=5):
    """
    Returns a boolean array with True if points are outliers and False 
    otherwise.

    Parameters:
    -----------
        points : An numobservations by numdimensions array of observations
        thresh : The modified z-score to use as a threshold. Observations with
            a modified z-score (based on the median absolute deviation) greater
            than this value will be classified as outliers.

    Returns:
    --------
        mask : A numobservations-length boolean array.

    References:
    ----------
        Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
        Handle Outliers", The ASQC Basic References in Quality Control:
        Statistical Techniques, Edward F. Mykytka, Ph.D., Editor. 
    """
    if len(points.shape) == 1:
        points = points[:,None]
    median = np.median(points, axis=0)
    diff = np.sum((points - median)**2, axis=-1)
    diff = np.sqrt(diff)
    med_abs_deviation = np.median(diff)

    modified_z_score = 0.6745 * diff / med_abs_deviation

    return modified_z_score > thresh

def plot_data(yRange=None):
    '''
    Plots and saves the cell measurement data.  Returns nothing.
    '''
    fig = plt.figure()
    ax = plt.subplot(111)
    plt.errorbar(range(len(avgCells.index)), avgCells[column], yerr=stdCells[column], fmt='o')
    ax = plt.gca()
    ax.set(xticks=range(len(avgCells.index)), xticklabels=avgCells.index)
    # adjust yRange if it was specified
    if yRange!=None:
        ax.set_ylim(yRange)
        fileName = column + ' exlcuding outliers'
    else:
        fileName = column
    plt.subplots_adjust(bottom=0.2, right=0.98, left=0.05)
    plt.title(column)
    locs, labels = plt.xticks()
    plt.setp(labels, rotation=90)
    mng = plt.get_current_fig_manager()
    mng.window.state('zoomed')
    plt.show()
    path1 = 'Y:/Test data/ACT02/vision inspection/plot_100_cells/with zeros removed/'
    path2 = 'Y:/Nate/git/nuvosun-python-lib/vision system/plot_100_cells/with zeros removed/'
    fig.savefig(path1 + fileName, bbox_inches = 'tight')
    fig.savefig(path2 + fileName, bbox_inches = 'tight')

plt.style.use('dark_background')

visionDF = pd.read_excel('C:/Users/nathan.george/Downloads/100 vision cells.xlsx')
cells = visionDF.groupby('Cell Id')
avgCells = cells.mean()
stdCells = cells.std()
print avgCells.index

atVisionColumns = False
for column in visionDF.columns:
    if column == 'Cell Length':
        atVisionColumns = True
    if atVisionColumns:
        plot_data()
        outliers = is_outlier(avgCells[column])
        non_outliers = np.array(avgCells[column])[~outliers]
        stdOutliers = is_outlier(stdCells[column])
        std_non_outliers = np.array(stdCells[column])[~stdOutliers]
        yRange = [(min(std_non_outliers) + min(non_outliers))*0.999, (max(std_non_outliers) + max(non_outliers))*1.001]
        plot_data(yRange = yRange)