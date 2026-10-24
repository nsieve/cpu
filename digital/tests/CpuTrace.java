import de.neemann.digital.cli.CircuitLoader;
import de.neemann.digital.core.Model;
import de.neemann.digital.core.ObservableValue;
import de.neemann.digital.core.element.Keys;
import de.neemann.digital.core.memory.DataField;
import de.neemann.digital.core.memory.EEPROM;
import de.neemann.digital.core.memory.RAMSinglePortSel;
import de.neemann.digital.draw.elements.Pin;
import de.neemann.digital.draw.elements.VisualElement;
import de.neemann.digital.draw.model.ModelCreator;
import de.neemann.digital.draw.model.ModelEntry;
import de.neemann.digital.gui.components.terminal.Keyboard;

import java.io.*;
import java.nio.file.Files;
import java.util.*;

// Runs CPU.dig with Digital's own simulator, without the GUI, with a program put in its
// EEPROM (the .dig file isn't changed), and writes the state of every clock cycle in the
// same format as emulator.py --cycle-trace:
//   cycle upc ir abus dbus control A X Y flags
// then the RAM bytes that aren't 0, and SPI_OUT, the LEDs and the MAX7219 digits at the end.
// It stops after the first cycle with nHALT on, or after maxCycles.
//
//   java -cp Digital.jar:. CpuTrace CPU.dig program.hex maxCycles out.txt [keys [interval]]
//
// The keys are typed right after the reset, or one every 'interval' cycles (the first one
// at cycle 'interval'), like someone typing while the program runs.
//
// check_cpu.py compiles and runs this, and compares it with the emulator.
public class CpuTrace {
    static final Map<String, ObservableValue> values = new HashMap<>();

    static void remember(String key, ObservableValue v) {
        if (v != null) values.putIfAbsent(key, v);
    }

    static ObservableValue get(String key) {
        ObservableValue v = values.get(key);
        if (v == null) throw new RuntimeException("signal not found in CPU.dig: " + key);
        return v;
    }

    // a value made of single-bit tunnels: name0, name1, ...
    static long bits(String module, String prefix, int count) {
        long v = 0;
        for (int i = 0; i < count; i++)
            v |= (get(module + ":" + prefix + i).getValue() & 1) << i;
        return v;
    }

    static String bus(ObservableValue v, int digits) {
        if (v.getHighZ() != 0) return "-".repeat(digits);
        return String.format("%0" + digits + "X", v.getValue());
    }

    public static void main(String[] args) throws Exception {
        File dig = new File(args[0]);
        long[] program = readHex(new File(args[1]));
        long maxCycles = Long.parseLong(args[2]);
        String keys = args.length > 4 ? args[4] : "";
        long interval = args.length > 5 ? Long.parseLong(args[5]) : 0;
        PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter(args[3])));

        CircuitLoader cl = new CircuitLoader(dig);
        ModelCreator mc = new ModelCreator(cl.getCircuit(), cl.getLibrary());
        Model m = mc.createModel(false);

        // every tunnel, splitter pin and register output, by module: "ALU.dig:AO3"
        for (ModelEntry e : mc) {
            VisualElement ve = e.getVisualElement(), cve = e.getContainingVisualElement();
            String module = cve == ve ? "TOP" : cve.getElementName();
            String name = ve.getElementName();
            String pos = ve.getPos().x + "," + ve.getPos().y;
            if (name.equals("Tunnel"))
                remember(module + ":" + ve.getElementAttributes().get(Keys.NETNAME), e.getPins().get(0).getValue());
            if (name.equals("Splitter"))
                for (Pin p : e.getPins())
                    remember(module + ":splitter@" + pos + ":" + p.getName(), p.getValue());
            if (name.equals("Register"))
                for (Pin p : e.getPins())
                    if (p.getName().equals("Q")) remember(module + ":register@" + pos, p.getValue());
        }

        EEPROM eeprom = m.findNode(EEPROM.class).get(0);
        DataField rom = new DataField(eeprom.getSize());
        for (int i = 0; i < program.length; i++) rom.setData(i, program[i]);
        eeprom.setData(rom);
        RAMSinglePortSel ram = m.findNode(RAMSinglePortSel.class).get(0);

        // the keys are typed after the reset: while the circuit settles, the keyboard's clock
        // input toggles, and every rising edge would take a key out of its buffer
        Deque<Integer> typed = new ArrayDeque<>();
        List<Keyboard> keyboards = m.findNode(Keyboard.class);
        for (Keyboard kb : keyboards)
            kb.setKeyboard(new Keyboard.KeyboardInterface() {
                public int getChar() { return typed.isEmpty() ? 0 : typed.peekFirst(); }
                public void deleteFirstChar() { typed.pollFirst(); }
            });

        ObservableValue abus = get("TOP:splitter@340,680:0-15");        // in front of the EEPROM
        ObservableValue dbus = get("ALU.dig:splitter@-500,420:0-7");     // D IN of the ALU
        ObservableValue c0 = get("TOP:splitter@1280,580:0-15");
        ObservableValue c1 = get("TOP:splitter@1440,580:0-15");
        ObservableValue c2 = get("TOP:splitter@1580,580:0-15");
        ObservableValue upc = get("CTRLUNIT.dig:splitter@440,600:0-3");
        ObservableValue spi = get("TOP:splitter@1540,-80:0-4");
        ObservableValue leds = get("TOP:splitter@1280,-60:0-7");
        ObservableValue nrst = get("TOP:nRST");
        ObservableValue nhalt = get("TOP:nHALT");

        m.init();
        ObservableValue clk = m.getInput("CLK");
        m.getInput("CLK_SEL").setValue(0);     // use the CLK input, not the real-time clock
        clk.setValue(0);
        m.doStep();

        // the power-on reset: clock until RST has been on and gone off again. Every line is
        // sampled right after a rising edge (CLK high): the registers have just loaded, and the
        // buses and control word are the ones of the new step. With CLK high the MAR, SP, X and
        // Y can't load (their async load is ORed with CLK), so nothing changes until the next edge.
        boolean sawReset = false;
        for (int edges = 0; edges < 20; edges++) {
            clk.setValue(1); m.doStep();
            if (nrst.getValue() == 0) sawReset = true;
            else if (sawReset) break;
            clk.setValue(0); m.doStep();
        }
        if (interval == 0) type(m, keyboards, typed, keys);
        out.println("# cycle upc ir abus dbus control A X Y flags");
        long cycle = 0;
        while (cycle < maxCycles) {
            if (interval > 0 && cycle > 0 && cycle % interval == 0 && cycle / interval <= keys.length())
                type(m, keyboards, typed, keys.substring((int) (cycle / interval) - 1, (int) (cycle / interval)));
            long ir = bits("IR.dig", "I", 16);
            long a = bits("ALU.dig", "AO", 8);
            long x = bits("RFILE.dig", "XO", 8);
            long y = bits("RFILE.dig", "YO", 8);
            long flags = (get("TOP:Z").getValue() & 1) | (get("TOP:C").getValue() & 1) << 1
                       | (get("TOP:N").getValue() & 1) << 2 | (get("TOP:V").getValue() & 1) << 3;
            long control = c0.getValue() | c1.getValue() << 16 | c2.getValue() << 32;
            out.printf("%d %X %04X %s %s %012X %02X %02X %02X %X%n", cycle, upc.getValue(), ir,
                       bus(abus, 4), bus(dbus, 2), control, a, x, y, flags);
            cycle++;
            if (nhalt.getValue() == 0) break;
            clk.setValue(0); m.doStep();
            clk.setValue(1); m.doStep();
        }
        out.println("# ram (address value, only the bytes that aren't 0)");
        DataField mem = ram.getMemory();
        for (int addr = 0; addr < 0xBF00; addr++) {
            long v = mem.getDataWord(addr);
            if (v != 0) out.printf("ram %04X %02X%n", addr, v);
        }
        out.printf("spi %02X%nleds %02X%n", spi.getValue(), leds.getValue());
        StringBuilder digits = new StringBuilder();
        for (int y = 760; y >= 200; y -= 80)    // DIG8 .. DIG1
            digits.append(String.format("%X", get("max7219_sim.dig:register@1340," + y).getValue()));
        out.println("display " + digits);
        out.println("keys " + typed.size());
        out.close();
    }

    // puts the keys in the keyboard buffer, and makes the keyboard update its outputs
    // (it only does that by itself when one of its inputs changes)
    static void type(Model m, List<Keyboard> keyboards, Deque<Integer> typed, String keys) {
        for (char ch : keys.toCharArray()) typed.add((int) ch);
        m.modify(() -> {
            try {
                for (Keyboard kb : keyboards) kb.writeOutputs();
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
    }

    static long[] readHex(File f) throws IOException {
        String[] tok = new String(Files.readAllBytes(f.toPath())).trim().split("\\s+");
        List<Long> words = new ArrayList<>();
        for (int i = 2; i < tok.length; i++) {      // after "v2.0 raw"
            String t = tok[i];
            if (t.contains("*")) {
                String[] p = t.split("\\*");
                for (int k = 0; k < Integer.parseInt(p[0]); k++) words.add(Long.parseLong(p[1], 16));
            } else words.add(Long.parseLong(t, 16));
        }
        long[] r = new long[words.size()];
        for (int i = 0; i < r.length; i++) r[i] = words.get(i);
        return r;
    }
}
