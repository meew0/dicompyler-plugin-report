import wx
from wx.lib.pubsub import pub
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from dicompyler import guidvh
import traceback

def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'RT Plan Report'
    props['description'] = "Generates a PDF report of a treatment plan, including DVH and structure dose metrics."
    props['author'] = 'meew0'
    props['version'] = 0.1
    props['plugin_type'] = 'export'
    props['menuname'] = 'Plan Report as PDF'
    props['plugin_version'] = 1
    props['min_dicom'] = ['rtdose', 'rtss']
    props['recommended_dicom'] = ['rtdose', 'rtss', 'rtplan']

    return props

class plugin:

    def __init__(self, parent):
        self.parent = parent

        # Initialise some attributes with None, so we can check for presence more easily later
        self.plan = None
        self.dvhs = None
        self.doses = None
        self.structures = None
        self.checked_structures = None

        self.patient_name = None
        self.patient_id = None

        # Subscribe to data parsed by dicompyler (not just by pydicom)
        pub.subscribe(self.on_update_patient, 'patient.updated.parsed_data')

        # Subscribe to structure checked state
        pub.subscribe(self.on_structures_checked, 'structures.checked')

    def on_update_patient(self, msg):
        """Update and load the patient data."""

        # RT plan data...
        if 'plan' in msg:
            self.plan = msg['plan']
        if 'dvhs' in msg:
            self.dvhs = msg['dvhs']
        if 'doses' in msg:
            self.doses = msg['doses']
        if 'structures' in msg:
            self.structures = msg['structures']

        # Demographic data...
        if 'name' in msg:
            # Reconstruct full name from DICOM components
            middle_name = msg['middle_name'] + ' ' if msg['middle_name'] != '' else ''
            given_name = msg['given_name'] + ' ' if msg['given_name'] != '' else ''
            self.patient_name = given_name + middle_name + msg['family_name']
        if 'id' in msg:
            self.patient_id = msg['id']
        if 'gender' in msg:
            self.patient_gender = msg['gender']
        if 'birth_date' in msg:
            # Insert delimiters into birth date for easier reading
            date_str = msg['birth_date']
            self.patient_birth_date = "{0}-{1}-{2}".format(date_str[0:4], date_str[4:6], date_str[6:8])

    def on_structures_checked(self, msg):
        """Update structure selection data."""
        self.checked_structures = msg

    def generate_structure_row(self, structure):
        dvh = self.dvhs[structure['id']]
        return [structure['name'], "%.2f" % dvh.volume, "%.2f" % dvh.min, "%.2f" % dvh.max, "%.2f" % dvh.mean, dvh.D50]

    def generate_structure_table(self, ax):
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.axis('off')
        ax.set_title("Structure Dose Metrics")

        data = [self.generate_structure_row(self.structures[id]) for id in self.checked_structures]

        column_labels=("Structure Name", "Volume [cm³]", "Min Dose [Gy]", "Max Dose [Gy]", "Mean Dose [Gy]", "D50 [Gy]")
        table = ax.table(cellText=data, colLabels=column_labels, loc='upper center')

        # Set cell heights to be a little closer together
        cells = table.properties()['child_artists']
        for cell in cells:
            cell.set_height(0.06)

    # Method mostly copied from Dicompyler itself
    def render_dvh_figure(self, fig, axes):
        """Render DVHs to figure"""

        axes.cla()
        maxlen = 1

        if self.dvhs is None:
            raise RuntimeError("No DVHs currently loaded!")

        if self.structures is None:
            raise RuntimeError("No structures currently loaded!")

        if self.checked_structures is None:
            raise RuntimeError("Some structures must be selected in order to generate a report!")

        for id, dvh in self.dvhs.items():
            if id in self.checked_structures:
                # Convert the color array to MPL formatted color
                colorarray = np.array(self.structures[id]['color'], dtype=float)

                # Plot white as black so it is visible on the plot
                if np.size(np.nonzero(colorarray/255 - 1)):
                    color = colorarray/255
                else:
                    color = np.zeros(3)

                # Some default values that shouldn't result in much difference from dicompyler's own rendering
                prefix = None
                linestyle = '-'
                scaling = None # dicompyler doesn't appear to actually use dose scaling anywhere

                maxlen = guidvh.guiDVH.DrawDVH(None, dvh.relative_volume.counts, self.structures[id], axes, color, maxlen, scaling, prefix, linestyle)
                axes.legend(fancybox=True, shadow=True)

        # set the axes parameters
        axes.grid(True)
        axes.set_xlim(0, maxlen)
        axes.set_ylim(0, 100)
        axes.set_xlabel('Dose (cGy)')
        axes.set_ylabel('Volume (%)')
        axes.set_title('DVH')

        # Add title with metadata
        axes.text(0.05, 0.95, "RT Treatment Plan Report", transform=fig.transFigure, size=24)
        axes.text(0.05, 0.93, "Patient {0}, born {1}, Gender: {2}, ID: {3}".format(self.patient_name, self.patient_birth_date, self.patient_gender, self.patient_id), transform=fig.transFigure, size=12)

        # Add plan info only if present
        if self.plan is not None:
            plan_type_string = "Brachytherapy" if self.plan['brachy'] else "External Beam"
            axes.text(0.05, 0.91, '{0} Plan "{1}", total dose: {2:d} cGy, PTV: "{3}"'.format(plan_type_string, self.plan['label'], self.plan['rxdose'], self.plan['name']), transform=fig.transFigure, size=12)

    def save_pdf(self, path):
        with PdfPages(path) as pdf:
            # Create figure and save to PDF
            fig, ax = plt.subplots(2, 1)
            fig.set_edgecolor('white')
            self.render_dvh_figure(fig, ax[0])
            self.generate_structure_table(ax[1])
            fig.set_size_inches(8.27, 11.69) # A4
            pdf.savefig(fig)

    def pluginMenu(self, evt):
        """Generate RT plan report."""

        with wx.FileDialog(self.parent, "Save PDF file", wildcard="PDF files (*.pdf)|*.pdf", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = file_dialog.GetPath()
            try:
                self.save_pdf(pathname)
                message = "Report created successfully."
                with wx.MessageDialog(self.parent, message, 'Plan Report', wx.OK | wx.ICON_INFORMATION) as message_dialog:
                    message_dialog.ShowModal()
            except Exception as e:
                print(traceback.format_exc())
                with wx.MessageDialog(self.parent, "An error occurred while saving report: " + str(e), 'Plan Report', wx.OK | wx.ICON_ERROR) as message_dialog:
                    message_dialog.ShowModal()
