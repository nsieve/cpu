import de.neemann.digital.cli.CircuitLoader;
import de.neemann.digital.core.element.Keys;
import de.neemann.digital.core.element.PinDescription;
import de.neemann.digital.core.io.In;
import de.neemann.digital.core.io.InValue;
import de.neemann.digital.core.io.Out;
import de.neemann.digital.draw.elements.Circuit;
import de.neemann.digital.draw.elements.Pin;
import de.neemann.digital.draw.elements.VisualElement;
import de.neemann.digital.draw.elements.Wire;
import de.neemann.digital.draw.graphics.Vector;
import de.neemann.digital.draw.shapes.ShapeFactory;
import de.neemann.digital.testing.TestCaseDescription;
import de.neemann.digital.testing.TestCaseElement;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

// Makes the test circuit of one module: the module embedded as a subcircuit, each of its
// pins wired to an input or an output with a name the test syntax accepts ("A IN" becomes
// A_IN, "[15:11]" becomes I15_11), and one Testcase per section of the tests file.
// The active-low inputs (nXXX) start at 1, like the pull resistors keep them in the CPU while
// it starts; a "defaults: NAME=VALUE ..." line before the first test case changes that.
//
//   java -cp Digital.jar:. ModuleWrapper DIR MODULE.dig TESTS.txt OUT.dig
//
// DIR has to hold the module and everything it uses (Digital only looks for subcircuits in
// the folder of the circuit it opens), so run_module_tests.py copies digital/ there first.
public class ModuleWrapper {
    static String testName(String label) {
        String name = label.replaceAll("[^A-Za-z0-9_]+", "_").replaceAll("^_+|_+$", "");
        return Character.isDigit(name.charAt(0)) ? "I" + name : name;
    }

    static int bitsOf(Circuit module, String label) {
        for (VisualElement e : module.getElements())
            if ((e.getElementName().equals("In") || e.getElementName().equals("Out"))
                    && label.equals(e.getElementAttributes().getLabel()))
                return e.getElementAttributes().get(Keys.BITS);
        return 1;
    }

    public static void main(String[] args) throws Exception {
        File dir = new File(args[0]);
        File module = new File(dir, args[1]);
        String text = new String(Files.readAllBytes(new File(args[2]).toPath()));
        File out = new File(dir, args[3]);

        // "defaults:" lines, before the first test case
        Map<String, Long> defaults = new HashMap<>();
        for (String line : text.split("\n")) {
            if (line.startsWith("## ")) break;
            if (line.startsWith("defaults:"))
                for (String d : line.substring(9).trim().split("\\s+"))
                    if (d.contains("=")) defaults.put(d.split("=")[0], Long.decode(d.split("=")[1]));
        }

        CircuitLoader cl = new CircuitLoader(module);
        ShapeFactory sf = cl.getShapeFactory();
        Circuit c = new Circuit();
        VisualElement mod = new VisualElement(module.getName()).setShapeFactory(sf).setPos(new Vector(0, 0));
        c.add(mod);

        int bottom = 0, n = 0;
        for (Pin p : mod.getPins()) {
            boolean input = p.getDirection() == PinDescription.Direction.input;
            int bits = bitsOf(cl.getCircuit(), p.getName());
            VisualElement io = new VisualElement(input ? In.DESCRIPTION.getName() : Out.DESCRIPTION.getName())
                    .setShapeFactory(sf)
                    .setAttribute(Keys.LABEL, testName(p.getName()))
                    .setAttribute(Keys.BITS, bits);
            if (input && bits > 1)
                io.setAttribute(Keys.IS_HIGH_Z, true);      // so a test can leave a bus input floating (Z)
            String name = testName(p.getName());
            boolean activeLow = name.length() > 1 && name.charAt(0) == 'n' && Character.isUpperCase(name.charAt(1));
            if (input && (defaults.containsKey(name) || activeLow))
                io.setAttribute(Keys.INPUT_DEFAULT, new InValue(defaults.getOrDefault(name, 1L)));
            int offset = n++ % 2 == 0 ? 80 : 200;           // staggered, so the shapes don't overlap
            Vector at = p.getPos().add(input ? -offset : offset, 0);
            io.setPos(at);
            c.add(io);
            c.add(new Wire(at, p.getPos()));
            bottom = Math.max(bottom, p.getPos().y);
        }

        // the sections of the tests file: "## name" starts a test case, everything
        // before the first one is a comment about the file
        List<String[]> sections = new ArrayList<>();
        for (String line : text.split("\n", -1)) {
            if (line.startsWith("## ")) sections.add(new String[]{line.substring(3).trim(), ""});
            else if (!sections.isEmpty()) sections.get(sections.size() - 1)[1] += line + "\n";
        }
        int y = bottom + 120;
        for (String[] s : sections) {
            VisualElement tc = new VisualElement(TestCaseElement.DESCRIPTION.getName())
                    .setShapeFactory(sf)
                    .setAttribute(Keys.LABEL, s[0])
                    .setAttribute(Keys.TESTDATA, new TestCaseDescription(s[1]))
                    .setPos(new Vector(0, y));
            c.add(tc);
            y += 120;
        }
        c.save(out);
    }
}
